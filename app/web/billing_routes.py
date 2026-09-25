"""Plans and PayPal checkout.

Flow: the browser renders PayPal's buttons -> POST /orders creates the order here with the plan's
price -> the buyer approves in PayPal's window -> POST /orders/<id>/capture verifies the order
(owner, plan, amount, currency), captures the money and extends the plan by 30 days.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Any

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import accounts
from app.db import session_scope, utcnow
from app.models import Payment, User
from app.plans import PAID_PLAN_IDS, PLAN_DURATION_DAYS, PLANS, get_plan
from app.web.paypal import PayPalClient, PayPalError
from app.web.security import ApiError, require_active, require_user

billing = Blueprint("billing", __name__, url_prefix="/api")
Body = tuple[dict[str, Any], int]


def _paypal() -> PayPalClient:
    client: PayPalClient | None = current_app.extensions.get("paypal")
    if client is None:
        raise ApiError(503, "Payments are not configured yet.")
    return client


@billing.get("/plans")
def plans() -> Body:
    return {"plans": [plan.to_dict() for plan in PLANS.values()]}, 200


@billing.get("/billing/config")
def config() -> Body:
    client: PayPalClient | None = current_app.extensions.get("paypal")
    if client is None:
        return {"enabled": False}, 200
    return {"enabled": True, "client_id": client.client_id, "currency": client.currency, "env": client.env}, 200


@billing.post("/billing/orders")
def create_order() -> Body:
    payload = request.get_json(silent=True) or {}
    plan_id = str(payload.get("plan", ""))
    if plan_id not in PAID_PLAN_IDS:
        raise ApiError(400, "Choose a paid plan.")
    client = _paypal()
    with session_scope() as db:
        user = require_user(db)
        require_active(user)
        custom_id = f"{user.id}:{plan_id}"
    try:
        order_id = client.create_order(plan=PLANS[plan_id], custom_id=custom_id)
    except PayPalError:
        raise ApiError(502, "PayPal is not available right now. Try again in a moment.") from None
    return {"order_id": order_id}, 201


def _unit(order: dict[str, Any]) -> dict[str, Any]:
    units = order.get("purchase_units") or [{}]
    unit: dict[str, Any] = units[0]
    return unit


@billing.post("/billing/orders/<order_id>/capture")
def capture_order(order_id: str) -> Body:
    client = _paypal()
    if not order_id.isalnum() or len(order_id) > 64:
        raise ApiError(400, "Invalid order.")
    now = utcnow()
    with session_scope() as db:
        user = require_user(db)
        existing = db.scalar(select(Payment).where(Payment.provider_order_id == order_id))
        if existing is not None:  # already captured (double click, retried request): idempotent
            if existing.user_id != user.id:
                raise ApiError(404, "Order not found.")
            return {"user": accounts.serialize_user(user, now, accounts.usage(db, user, now))}, 200

        try:
            order = client.get_order(order_id)
        except PayPalError:
            raise ApiError(502, "Could not verify the order with PayPal.") from None
        unit = _unit(order)
        owner, _, plan_id = str(unit.get("custom_id", "")).partition(":")
        amount = unit.get("amount") or {}
        plan = get_plan(plan_id)
        if owner != str(user.id) or plan_id not in PAID_PLAN_IDS:
            raise ApiError(404, "Order not found.")
        if amount.get("currency_code") != client.currency or Decimal(str(amount.get("value", "0"))) != plan.price_usd:
            raise ApiError(400, "The order amount does not match the plan price.")

        try:
            captured = client.capture_order(order_id)
        except PayPalError:
            raise ApiError(502, "PayPal could not capture the payment. You were not charged twice.") from None
        captures = (_unit(captured).get("payments") or {}).get("captures") or [{}]
        capture = captures[0]
        if captured.get("status") != "COMPLETED" or capture.get("status") != "COMPLETED":
            raise ApiError(402, "The payment was not completed.")

        # Extend an active pass of the same plan; otherwise the new plan starts now.
        active_same_plan = user.plan == plan.id and user.plan_expires_at is not None and user.plan_expires_at > now
        start = user.plan_expires_at if active_same_plan and user.plan_expires_at else now
        user.plan = plan.id
        user.plan_expires_at = start + timedelta(days=PLAN_DURATION_DAYS)
        db.add(
            Payment(
                user_id=user.id,
                provider="paypal",
                provider_order_id=order_id,
                plan=plan.id,
                amount=plan.price_usd,
                currency=client.currency,
                status="COMPLETED",
            )
        )
        try:
            db.flush()
        except IntegrityError:  # the same order captured concurrently: the other request recorded it
            raise ApiError(409, "This payment was already recorded.") from None
        return {"user": accounts.serialize_user(user, now, accounts.usage(db, user, now))}, 200


@billing.get("/billing/payments")
def my_payments() -> Body:
    with session_scope() as db:
        user: User = require_user(db)
        rows = db.execute(
            select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
        ).scalars()
        payments = [
            {
                "plan": p.plan,
                "amount": f"{p.amount:.2f}",
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in rows
        ]
    return {"payments": payments, "duration_days": PLAN_DURATION_DAYS}, 200
