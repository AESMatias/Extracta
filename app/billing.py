"""Billing rules: one-time 30-day passes, monthly subscriptions, refunds and PayPal webhooks.

Framework-free: the HTTP routes, the webhook endpoint and the periodic reconciliation task all
call these functions with an open SQLAlchemy session and a PayPal client. Nothing here trusts
the browser: owner, plan, amount and currency always come from PayPal and are checked here.

Plan time:
- One-time pass: 30 days, added after the current pass when it is the same plan.
- Subscription: until the next billing date plus GRACE, so a renewal that PayPal charges a bit
  late never interrupts the service. Each renewal moves it one month further. Cancelling keeps
  the plan until the paid period ends (the grace is dropped).
- Refund or reversal: the payment is marked and the plan it paid for ends now.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, PayPalPlan, Subscription, User, WebhookEvent
from app.plans import PAID_PLAN_IDS, PLAN_DURATION_DAYS, Plan, get_plan

log = logging.getLogger(__name__)

GRACE = timedelta(days=3)
# A user with one of these cannot start another subscription (they must cancel first).
BLOCKING_STATUSES = ("APPROVED", "ACTIVE", "SUSPENDED")
# Subscriptions the reconciliation task keeps in sync with PayPal.
LIVE_STATUSES = ("APPROVAL_PENDING", "APPROVED", "ACTIVE", "SUSPENDED")


class PayPalApi(Protocol):
    env: str
    currency: str

    def get_order(self, order_id: str) -> dict[str, Any]: ...
    def capture_order(self, order_id: str) -> dict[str, Any]: ...
    def create_product(self) -> str: ...
    def create_billing_plan(self, *, product_id: str, plan: Plan) -> str: ...
    def create_subscription(self, *, paypal_plan_id: str, custom_id: str, start_time: datetime | None) -> str: ...
    def get_subscription(self, subscription_id: str) -> dict[str, Any]: ...
    def cancel_subscription(self, subscription_id: str, *, reason: str) -> None: ...


@dataclass
class BillingError(Exception):
    """A problem to report to the caller; the message is safe to show."""

    status: int
    message: str

    def __str__(self) -> str:
        return self.message


def _not_found(what: str) -> BillingError:
    return BillingError(404, f"{what} not found.")


def parse_time(value: object) -> datetime | None:
    """PayPal timestamps look like 2026-10-25T10:00:00Z."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _owner_and_plan(custom_id: object) -> tuple[uuid.UUID, str] | None:
    owner, _, plan_id = str(custom_id or "").partition(":")
    try:
        return uuid.UUID(owner), plan_id
    except ValueError:
        return None


# --------------------------------------------------------------------------- one-time passes


def _unit(order: dict[str, Any]) -> dict[str, Any]:
    units = order.get("purchase_units") or [{}]
    unit: dict[str, Any] = units[0]
    return unit


def _first_capture(order: dict[str, Any]) -> dict[str, Any]:
    captures = (_unit(order).get("payments") or {}).get("captures") or [{}]
    capture: dict[str, Any] = captures[0]
    return capture


def fulfil_order(db: Session, client: PayPalApi, order_id: str, *, user: User | None, now: datetime) -> User:
    """Capture an approved order (or record one already captured) and extend the buyer's plan.

    Called by the browser after approval (`user` = the signed-in account) and by the webhook when
    the browser never came back (`user` = None). Safe to call twice for the same order.
    """
    existing = db.scalar(select(Payment).where(Payment.provider_order_id == order_id))
    if existing is not None:
        if user is not None and existing.user_id != user.id:
            raise _not_found("Order")
        owner = db.get(User, existing.user_id)
        if owner is None:
            raise _not_found("Order")
        return owner

    order = client.get_order(order_id)
    unit = _unit(order)
    parsed = _owner_and_plan(unit.get("custom_id"))
    if parsed is None or parsed[1] not in PAID_PLAN_IDS:
        raise _not_found("Order")
    owner_id, plan_id = parsed
    if user is not None and owner_id != user.id:
        raise _not_found("Order")
    owner = user or db.get(User, owner_id)
    if owner is None:
        raise _not_found("Order")
    plan = get_plan(plan_id)
    amount = unit.get("amount") or {}
    if amount.get("currency_code") != client.currency or Decimal(str(amount.get("value", "0"))) != plan.price_usd:
        raise BillingError(400, "The order amount does not match the plan price.")

    if order.get("status") == "APPROVED":
        order = client.capture_order(order_id)  # idempotent at PayPal: same request ID per order
    capture = _first_capture(order)
    if order.get("status") != "COMPLETED" or capture.get("status") != "COMPLETED":
        raise BillingError(402, "The payment was not completed.")

    payment = Payment(
        user_id=owner.id,
        provider="paypal",
        kind="pass",
        provider_order_id=order_id,
        provider_capture_id=capture.get("id") or None,
        plan=plan.id,
        amount=plan.price_usd,
        currency=client.currency,
        status="COMPLETED",
    )
    try:
        with db.begin_nested():  # the browser and the webhook may record the same order at once
            db.add(payment)
            db.flush()
    except IntegrityError:
        return owner  # the other one recorded it and extended the plan

    # Extend an active pass of the same plan; otherwise the new plan starts now.
    active_same_plan = owner.plan == plan.id and owner.plan_expires_at is not None and owner.plan_expires_at > now
    start = owner.plan_expires_at if active_same_plan and owner.plan_expires_at else now
    owner.plan = plan.id
    owner.plan_expires_at = start + timedelta(days=PLAN_DURATION_DAYS)
    return owner


# --------------------------------------------------------------------------- subscriptions


def paypal_plan_id(db: Session, client: PayPalApi, plan: Plan) -> str:
    """The PayPal billing plan for this plan and price, created the first time it is needed."""
    query = select(PayPalPlan).where(
        PayPalPlan.env == client.env, PayPalPlan.plan == plan.id, PayPalPlan.price == plan.price_usd
    )
    row = db.scalar(query)
    if row is not None:
        return row.paypal_plan_id
    product = db.scalar(select(PayPalPlan.paypal_product_id).where(PayPalPlan.env == client.env).limit(1))
    product_id = product or client.create_product()
    new_id = client.create_billing_plan(product_id=product_id, plan=plan)
    try:
        with db.begin_nested():
            db.add(
                PayPalPlan(
                    env=client.env,
                    plan=plan.id,
                    price=plan.price_usd,
                    paypal_product_id=product_id,
                    paypal_plan_id=new_id,
                )
            )
            db.flush()
    except IntegrityError:  # created at the same time by another request: use the stored one
        stored = db.scalar(query)
        if stored is not None:
            return stored.paypal_plan_id
        raise
    return new_id


def _plan_of_paypal_plan(db: Session, env: str, paypal_plan: object) -> str | None:
    return db.scalar(
        select(PayPalPlan.plan).where(PayPalPlan.env == env, PayPalPlan.paypal_plan_id == str(paypal_plan))
    )


def start_subscription(db: Session, client: PayPalApi, user: User, plan: Plan, now: datetime) -> str:
    """Create the subscription at PayPal; the buyer then approves it in PayPal's window."""
    blocking = db.scalar(
        select(Subscription.id).where(Subscription.user_id == user.id, Subscription.status.in_(BLOCKING_STATUSES))
    )
    if blocking is not None:
        raise BillingError(409, "You already have a subscription. Cancel it first to change plans.")
    # Already paid for this plan (a one-time pass)? The first charge waits until it ends.
    start: datetime | None = None
    if user.plan == plan.id and user.plan_expires_at is not None and user.plan_expires_at > now + timedelta(days=1):
        start = user.plan_expires_at
    subscription_id = client.create_subscription(
        paypal_plan_id=paypal_plan_id(db, client, plan), custom_id=f"{user.id}:{plan.id}", start_time=start
    )
    db.add(
        Subscription(
            user_id=user.id,
            provider_subscription_id=subscription_id,
            plan=plan.id,
            status="APPROVAL_PENDING",
            next_billing_at=start,
        )
    )
    return subscription_id


def _end_paid_period(owner: User, subscription: Subscription, paid_until: datetime | None, now: datetime) -> None:
    """No more renewals: keep the plan until the paid period ends, without the grace days."""
    if subscription.cancelled_at is None:
        subscription.cancelled_at = now
    if owner.plan == subscription.plan and owner.plan_expires_at is not None and paid_until is not None:
        owner.plan_expires_at = min(owner.plan_expires_at, max(paid_until, now))


def sync_subscription(
    db: Session, client: PayPalApi, provider_subscription_id: str, *, user: User | None, now: datetime
) -> Subscription:
    """Read the subscription from PayPal, check it is ours, store its state and apply it to the plan."""
    data = client.get_subscription(provider_subscription_id)
    parsed = _owner_and_plan(data.get("custom_id"))
    plan_id = _plan_of_paypal_plan(db, client.env, data.get("plan_id"))
    if parsed is None or plan_id is None or parsed[1] != plan_id:
        raise _not_found("Subscription")  # not created by this app, or tampered with
    owner_id = parsed[0]
    if user is not None and owner_id != user.id:
        raise _not_found("Subscription")
    owner = user or db.get(User, owner_id)
    if owner is None:
        raise _not_found("Subscription")

    subscription = db.scalar(
        select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
    )
    if subscription is None:
        subscription = Subscription(user_id=owner.id, provider_subscription_id=provider_subscription_id, plan=plan_id)
        db.add(subscription)
    elif subscription.user_id != owner.id:
        raise _not_found("Subscription")

    paid_until = subscription.next_billing_at  # PayPal drops the next billing time once cancelled
    status = str(data.get("status", "")).upper()
    next_billing = parse_time((data.get("billing_info") or {}).get("next_billing_time"))
    subscription.status = status
    if next_billing is not None:
        subscription.next_billing_at = next_billing

    if status == "ACTIVE":
        until = (next_billing or now + timedelta(days=PLAN_DURATION_DAYS)) + GRACE
        keep = owner.plan_expires_at if owner.plan == plan_id and owner.plan_expires_at is not None else None
        owner.plan = plan_id
        owner.plan_expires_at = max(until, keep) if keep is not None else until
    elif status in ("CANCELLED", "EXPIRED"):
        _end_paid_period(owner, subscription, paid_until, parse_time(data.get("status_update_time")) or now)
    db.flush()
    return subscription


def cancel_subscription(db: Session, client: PayPalApi, user: User, now: datetime) -> Subscription:
    subscription = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status.in_(BLOCKING_STATUSES))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    if subscription is None:
        raise BillingError(404, "You have no active subscription.")
    client.cancel_subscription(subscription.provider_subscription_id, reason="Cancelled by the customer")
    subscription.status = "CANCELLED"
    _end_paid_period(user, subscription, subscription.next_billing_at, now)
    db.flush()
    return subscription


def record_sale(db: Session, client: PayPalApi, sale: dict[str, Any], now: datetime) -> None:
    """A subscription payment (first charge or renewal): record it and extend the plan."""
    sale_id = str(sale.get("id", ""))
    subscription_id = sale.get("billing_agreement_id")
    if not sale_id or not subscription_id:
        return  # not a subscription payment
    if db.scalar(select(Payment.id).where(Payment.provider_order_id == sale_id)) is not None:
        return
    subscription = sync_subscription(db, client, str(subscription_id), user=None, now=now)
    amount = sale.get("amount") or {}
    try:
        with db.begin_nested():
            db.add(
                Payment(
                    user_id=subscription.user_id,
                    provider="paypal",
                    kind="subscription",
                    provider_order_id=sale_id,
                    provider_capture_id=sale_id,
                    subscription_id=subscription.id,
                    plan=subscription.plan,
                    amount=Decimal(str(amount.get("total", "0"))),
                    currency=str(amount.get("currency", client.currency))[:3],
                    status="COMPLETED",
                )
            )
            db.flush()
    except IntegrityError:
        pass  # recorded by a concurrent delivery


def revoke_payment(db: Session, capture_id: str, status: str, now: datetime) -> None:
    """A refund or reversal: mark the payment and end the plan time it bought."""
    payment = db.scalar(select(Payment).where(Payment.provider_capture_id == capture_id))
    if payment is None or payment.status == status:
        return
    payment.status = status
    owner = db.get(User, payment.user_id)
    if owner is not None and owner.plan == payment.plan and owner.plan_expires_at and owner.plan_expires_at > now:
        owner.plan_expires_at = now
    log.warning("Payment %s was %s: the plan it paid for ended.", payment.provider_order_id, status.lower())


# --------------------------------------------------------------------------- webhooks

_SUBSCRIPTION_EVENTS = {
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.UPDATED",
    "BILLING.SUBSCRIPTION.RE-ACTIVATED",
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.EXPIRED",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
}


def _capture_id_from_refund(refund: dict[str, Any]) -> str | None:
    """A refund names its capture only in its "up" link: .../v2/payments/captures/<id>."""
    for link in refund.get("links") or []:
        if link.get("rel") == "up" and "/captures/" in str(link.get("href", "")):
            return str(link["href"]).rstrip("/").rsplit("/", 1)[-1]
    return None


def _apply_event(db: Session, client: PayPalApi, event_type: str, resource: dict[str, Any], now: datetime) -> None:
    try:
        if event_type in _SUBSCRIPTION_EVENTS:
            sync_subscription(db, client, str(resource.get("id", "")), user=None, now=now)
        elif event_type == "PAYMENT.SALE.COMPLETED":
            record_sale(db, client, resource, now)
        elif event_type == "PAYMENT.SALE.REFUNDED":
            revoke_payment(db, str(resource.get("sale_id", "")), "REFUNDED", now)
        elif event_type == "PAYMENT.SALE.REVERSED":
            revoke_payment(db, str(resource.get("id", "")), "REVERSED", now)
        elif event_type == "CHECKOUT.ORDER.APPROVED":
            fulfil_order(db, client, str(resource.get("id", "")), user=None, now=now)
        elif event_type == "PAYMENT.CAPTURE.COMPLETED":
            order_id = ((resource.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id")
            if order_id:
                fulfil_order(db, client, str(order_id), user=None, now=now)
        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            capture_id = _capture_id_from_refund(resource)
            if capture_id:
                revoke_payment(db, capture_id, "REFUNDED", now)
        elif event_type == "PAYMENT.CAPTURE.REVERSED":
            revoke_payment(db, str(resource.get("id", "")), "REVERSED", now)
    except BillingError as exc:
        if exc.status != 404:
            raise
        log.info("Ignoring %s: it does not belong to this app.", event_type)


def process_webhook(db: Session, client: PayPalApi, event: dict[str, Any], now: datetime) -> str:
    """Apply a verified PayPal event once. Returns "processed" or "duplicate".

    The event is recorded in the same transaction as its effects: if anything fails, nothing is
    kept and PayPal delivers it again later.
    """
    event_id = str(event.get("id", ""))[:64]
    event_type = str(event.get("event_type", ""))[:64]
    if not event_id:
        raise BillingError(400, "The event has no id.")
    if db.scalar(select(WebhookEvent.id).where(WebhookEvent.provider_event_id == event_id)) is not None:
        return "duplicate"
    resource = event.get("resource") if isinstance(event.get("resource"), dict) else {}
    assert isinstance(resource, dict)
    _apply_event(db, client, event_type, resource, now)
    try:
        with db.begin_nested():
            resource_id = resource.get("id")
            db.add(
                WebhookEvent(
                    provider_event_id=event_id,
                    event_type=event_type,
                    resource_id=str(resource_id)[:64] if resource_id else None,
                )
            )
            db.flush()
    except IntegrityError:
        return "duplicate"  # the same event delivered twice at the same time
    return "processed"


# --------------------------------------------------------------------------- reconciliation


def reconcile_subscriptions(db: Session, client: PayPalApi, now: datetime, *, limit: int = 100) -> int:
    """Re-read subscriptions whose billing date passed (or that never finished activating).

    Webhooks can be lost or delayed; this makes sure a paying user is never left on Free and a
    cancelled one does not keep a paid plan. Returns how many subscriptions were checked.
    """
    due = db.scalars(
        select(Subscription)
        .where(
            Subscription.status.in_(LIVE_STATUSES),
            Subscription.created_at > now - timedelta(days=400),
            (Subscription.next_billing_at.is_(None)) | (Subscription.next_billing_at < now - timedelta(hours=1)),
        )
        .order_by(Subscription.updated_at)
        .limit(limit)
    ).all()
    checked = 0
    for subscription in due:
        if subscription.status == "APPROVAL_PENDING" and subscription.created_at < now - timedelta(days=3):
            subscription.status = "ABANDONED"  # the buyer never approved it
            continue
        try:
            with db.begin_nested():
                sync_subscription(db, client, subscription.provider_subscription_id, user=None, now=now)
            checked += 1
        except Exception:  # one failure must not stop the others; the next run retries it
            log.exception("Could not reconcile subscription %s", subscription.provider_subscription_id)
    return checked
