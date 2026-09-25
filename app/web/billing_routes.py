"""Plans, PayPal checkout (one-time passes and monthly subscriptions) and PayPal webhooks.

One-time pass: the browser renders PayPal's buttons -> POST /billing/orders creates the order
here with the plan's price -> the buyer approves in PayPal's window -> POST
/billing/orders/<id>/capture verifies the order (owner, plan, amount, currency), captures the
money and extends the plan by 30 days.

Subscription: POST /billing/subscriptions creates it here -> the buyer approves -> POST
/billing/subscriptions/<id>/activate reads it back from PayPal and applies the plan. Renewals,
cancellations and refunds arrive at POST /billing/webhook, signed by PayPal.

The rules live in app/billing.py; these routes only handle HTTP.
"""

import json
from collections.abc import Callable
from typing import Any

from flask import Blueprint, current_app, request
from sqlalchemy import select

from app import accounts, billing
from app.db import session_scope, utcnow
from app.models import Payment, User
from app.plans import PAID_PLAN_IDS, PLAN_DURATION_DAYS, PLANS
from app.web.paypal import PayPalClient, PayPalError
from app.web.security import ApiError, client_ip, rate_limit, require_active, require_user, require_verified, settings

billing_api = Blueprint("billing", __name__, url_prefix="/api")
Body = tuple[dict[str, Any], int]
MAX_WEBHOOK_BYTES = 256 * 1024


def _paypal() -> PayPalClient:
    client: PayPalClient | None = current_app.extensions.get("paypal")
    if client is None:
        raise ApiError(503, "Payments are not configured yet.")
    return client


def _run[T](action: Callable[[], T], unavailable: str) -> T:
    """Turn billing and PayPal failures into API errors."""
    try:
        return action()
    except billing.BillingError as exc:
        raise ApiError(exc.status, exc.message) from None
    except PayPalError:
        raise ApiError(502, unavailable) from None


def _paid_plan(payload: dict[str, Any]) -> str:
    plan_id = str(payload.get("plan", ""))
    if plan_id not in PAID_PLAN_IDS:
        raise ApiError(400, "Choose a paid plan.")
    return plan_id


def _can_pay(user: User) -> None:
    require_active(user)
    require_verified(user)


@billing_api.get("/plans")
def plans() -> Body:
    return {"plans": [plan.to_dict() for plan in PLANS.values()]}, 200


@billing_api.get("/billing/config")
def config() -> Body:
    client: PayPalClient | None = current_app.extensions.get("paypal")
    if client is None:
        return {"enabled": False}, 200
    return {"enabled": True, "client_id": client.client_id, "currency": client.currency, "env": client.env}, 200


# --------------------------------------------------------------------------- one-time passes


@billing_api.post("/billing/orders")
def create_order() -> Body:
    plan_id = _paid_plan(request.get_json(silent=True) or {})
    client = _paypal()
    with session_scope() as db:
        user = require_user(db)
        _can_pay(user)
        _run(lambda: billing.ensure_no_live_subscription(db, user), "")
        custom_id = f"{user.id}:{plan_id}"
    order_id = _run(
        lambda: client.create_order(plan=PLANS[plan_id], custom_id=custom_id),
        "PayPal is not available right now. Try again in a moment.",
    )
    return {"order_id": order_id}, 201


@billing_api.post("/billing/orders/<order_id>/capture")
def capture_order(order_id: str) -> Body:
    client = _paypal()
    if not order_id.isalnum() or len(order_id) > 64:
        raise ApiError(400, "Invalid order.")
    now = utcnow()
    with session_scope() as db:
        user = require_user(db)
        _run(
            lambda: billing.fulfil_order(db, client, order_id, user=user, now=now),
            "Could not complete the payment with PayPal. You were not charged twice; try again.",
        )
        return {"user": accounts.describe(db, user, now)}, 200


# --------------------------------------------------------------------------- subscriptions


def _subscription_id(value: str) -> str:
    if not value.replace("-", "").isalnum() or len(value) > 64:
        raise ApiError(400, "Invalid subscription.")
    return value


@billing_api.post("/billing/subscriptions")
def create_subscription() -> Body:
    plan_id = _paid_plan(request.get_json(silent=True) or {})
    client = _paypal()
    now = utcnow()
    with session_scope() as db:
        user = require_user(db)
        _can_pay(user)
        rate_limit(f"subscribe:{user.id}", limit=10, window_seconds=3600)
        subscription_id = _run(
            lambda: billing.start_subscription(db, client, user, PLANS[plan_id], now),
            "PayPal is not available right now. Try again in a moment.",
        )
    return {"subscription_id": subscription_id}, 201


@billing_api.post("/billing/subscriptions/<subscription_id>/activate")
def activate_subscription(subscription_id: str) -> Body:
    client = _paypal()
    provider_id = _subscription_id(subscription_id)
    now = utcnow()
    with session_scope() as db:
        user = require_user(db)
        subscription = _run(
            lambda: billing.sync_subscription(db, client, provider_id, user=user, now=now),
            "Could not confirm the subscription with PayPal. It will be applied automatically in a few minutes.",
        )
        body = {"user": accounts.describe(db, user, now), "status": subscription.status}
    # APPROVED: PayPal is still charging the first payment; the webhook finishes the activation.
    return body, 200 if subscription.status == "ACTIVE" else 202


@billing_api.post("/billing/subscription/cancel")
def cancel_subscription() -> Body:
    client = _paypal()
    now = utcnow()
    with session_scope() as db:
        user = require_user(db)
        _run(
            lambda: billing.cancel_subscription(db, client, user, now),
            "PayPal could not cancel the subscription right now. Try again in a moment.",
        )
        return {"user": accounts.describe(db, user, now)}, 200


# --------------------------------------------------------------------------- history


@billing_api.get("/billing/payments")
def my_payments() -> Body:
    with session_scope() as db:
        user: User = require_user(db)
        rows = db.execute(
            select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
        ).scalars()
        payments = [
            {
                "plan": p.plan,
                "kind": p.kind,
                "amount": f"{p.amount:.2f}",
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in rows
        ]
    return {"payments": payments, "duration_days": PLAN_DURATION_DAYS}, 200


# --------------------------------------------------------------------------- webhook


@billing_api.post("/billing/webhook")
def webhook() -> Body:
    """PayPal's server calls this; there is no browser session. Every event is verified first."""
    client = _paypal()
    webhook_id = settings().paypal_webhook_id
    if not webhook_id:
        raise ApiError(503, "Webhooks are not configured: set PAYPAL_WEBHOOK_ID.")
    rate_limit(f"webhook:{client_ip()}", limit=300, window_seconds=60)
    request.max_content_length = MAX_WEBHOOK_BYTES
    raw_body = request.get_data(as_text=True)
    headers = {key.upper(): value for key, value in request.headers.items()}
    verified = _run(
        lambda: client.verify_webhook(headers=headers, raw_body=raw_body, webhook_id=webhook_id),
        "Could not verify the event with PayPal.",  # 502: PayPal retries later
    )
    if not verified:
        raise ApiError(400, "Invalid webhook signature.")
    event = json.loads(raw_body)  # verify_webhook already checked it is a JSON object
    with session_scope() as db:
        result = _run(
            lambda: billing.process_webhook(db, client, event, utcnow()),
            "PayPal is not available right now.",
        )
    return {"result": result}, 200
