"""Administration: sign in with ADMIN_PASSWORD, review accounts, approve or reject them, and set
plans, expiry dates and custom daily limits. Every privilege a user has is listed explicitly.
"""

import hmac
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Literal

from flask import Blueprint, request, session
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, or_, select

from app import accounts
from app.db import session_scope, utcnow
from app.models import Payment, Subscription, UsageEvent, User
from app.plans import PLANS
from app.schemas import summarize_validation_error
from app.web.security import ApiError, client_ip, rate_limit, settings

admin = Blueprint("admin", __name__, url_prefix="/api/admin")
Body = tuple[dict[str, Any], int]
ADMIN_SESSION = timedelta(hours=2)
_ADMIN_KEY = "admin_until"


def _is_admin() -> bool:
    until = session.get(_ADMIN_KEY)
    return isinstance(until, int | float) and until > utcnow().timestamp()


def admin_required[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not settings().admin_enabled:
            raise ApiError(404, "Administration is disabled: set ADMIN_PASSWORD.")
        if not _is_admin():
            raise ApiError(401, "Administrator sign-in required.")
        return view(*args, **kwargs)

    return wrapper


@admin.get("/session")
def admin_session() -> Body:
    return {"enabled": settings().admin_enabled, "authenticated": _is_admin()}, 200


@admin.post("/login")
def admin_login() -> Body:
    config = settings()
    if config.admin_password is None:
        raise ApiError(404, "Administration is disabled: set ADMIN_PASSWORD.")
    rate_limit(f"admin-login:{client_ip()}", limit=5, window_seconds=900)  # 5 attempts per 15 minutes
    payload = request.get_json(silent=True) or {}
    password = str(payload.get("password", ""))
    if not hmac.compare_digest(password.encode(), config.admin_password.get_secret_value().encode()):
        raise ApiError(401, "Wrong administrator password.")
    session[_ADMIN_KEY] = (utcnow() + ADMIN_SESSION).timestamp()
    return {"authenticated": True, "expires_in_seconds": int(ADMIN_SESSION.total_seconds())}, 200


@admin.post("/logout")
def admin_logout() -> Body:
    session.pop(_ADMIN_KEY, None)
    return {"authenticated": False}, 200


def _admin_user(
    user: User,
    used_24h: int,
    total_uploads: int,
    paid_total: str,
    subscription: Subscription | None,
    now: datetime,
) -> dict[str, Any]:
    data = accounts.serialize_user(user, now)
    plan = accounts.current_plan(user, now)
    privileges = plan.privileges()
    privileges["docs_per_24h"] = accounts.daily_limit(user, now)  # includes any admin override
    data.update(
        {
            "assigned_plan": user.plan,  # may differ from the effective plan when the pass expired
            "raw_plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "daily_limit_override": user.daily_limit_override,
            "privileges": privileges,
            "uploads_24h": used_24h,
            "uploads_total": total_uploads,
            "paid_total_usd": paid_total,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "sign_in_methods": [m for m, on in (("password", user.password_hash), ("google", user.google_sub)) if on],
            "subscription": accounts.serialize_subscription(subscription),
        }
    )
    return data


@admin.get("/users")
@admin_required
def list_users() -> Body:
    now = utcnow()
    status = request.args.get("status")
    query = (request.args.get("q") or "").strip().lower()
    with session_scope() as db:
        stmt = select(User).order_by(User.created_at.desc()).limit(500)
        if status in ("pending", "active", "rejected", "suspended"):
            stmt = stmt.where(User.status == status)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(or_(User.email.ilike(like), User.name.ilike(like)))
        users = db.execute(stmt).scalars().all()
        ids = [user.id for user in users]
        recent = dict(
            db.execute(
                select(UsageEvent.user_id, func.count())
                .where(UsageEvent.user_id.in_(ids), UsageEvent.created_at > now - accounts.QUOTA_WINDOW)
                .group_by(UsageEvent.user_id)
            )
            .tuples()
            .all()
        )
        totals = dict(
            db.execute(
                select(UsageEvent.user_id, func.count()).where(UsageEvent.user_id.in_(ids)).group_by(UsageEvent.user_id)
            )
            .tuples()
            .all()
        )
        paid = dict(
            db.execute(
                select(Payment.user_id, func.sum(Payment.amount))
                .where(Payment.user_id.in_(ids), Payment.status == "COMPLETED")
                .group_by(Payment.user_id)
            )
            .tuples()
            .all()
        )
        latest: dict[Any, Subscription] = {}
        for sub in db.scalars(
            select(Subscription)
            .where(Subscription.user_id.in_(ids), Subscription.status != "APPROVAL_PENDING")
            .order_by(Subscription.created_at)
        ):
            latest[sub.user_id] = sub  # ordered oldest first: the newest one wins
        items = [
            _admin_user(
                u, recent.get(u.id, 0), totals.get(u.id, 0), f"{paid.get(u.id) or 0:.2f}", latest.get(u.id), now
            )
            for u in users
        ]
    return {"users": items, "plans": [plan.to_dict() for plan in PLANS.values()]}, 200


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "active", "rejected", "suspended"] | None = None
    plan: Literal["free", "starter", "pro", "business", "ultra"] | None = None
    plan_expires_at: datetime | None = None  # ISO 8601 with timezone; null = no expiry
    daily_limit_override: int | None = Field(default=None, ge=0, le=100_000)  # null = use the plan's limit
    email_verified: bool | None = None  # true marks the address verified (e.g. confirmed by phone)


@admin.patch("/users/<user_id>")
@admin_required
def update_user(user_id: str) -> Body:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise ApiError(404, "User not found.") from None
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "Send a JSON body.")
    try:
        update = UserUpdate.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(400, "Invalid changes.", details=summarize_validation_error(exc)) from None
    if update.plan_expires_at is not None and update.plan_expires_at.tzinfo is None:
        raise ApiError(400, "plan_expires_at needs a timezone, e.g. 2026-12-31T23:59:59Z.")

    now = utcnow()
    with session_scope() as db:
        user = db.get(User, uid)
        if user is None:
            raise ApiError(404, "User not found.")
        for field in update.model_fields_set - {"email_verified"}:  # only what the admin sent; null clears
            setattr(user, field, getattr(update, field))
        if "email_verified" in update.model_fields_set:
            user.email_verified_at = (user.email_verified_at or now) if update.email_verified else None
        if user.plan == "free":
            user.plan_expires_at = None
        db.flush()
        used = accounts.usage(db, user, now).used
        return {"user": _admin_user(user, used, 0, "0.00", accounts.current_subscription(db, user), now)}, 200


@admin.get("/payments")
@admin_required
def list_payments() -> Body:
    with session_scope() as db:
        rows = db.execute(
            select(Payment, User.email)
            .join(User, User.id == Payment.user_id)
            .order_by(Payment.created_at.desc())
            .limit(500)
        ).all()
        payments = [
            {
                "id": str(p.id),
                "email": email,
                "plan": p.plan,
                "kind": p.kind,
                "amount": f"{p.amount:.2f}",
                "currency": p.currency,
                "status": p.status,
                "provider_order_id": p.provider_order_id,
                "created_at": p.created_at.isoformat(),
            }
            for p, email in rows
        ]
    return {"payments": payments}, 200


@admin.get("/stats")
@admin_required
def stats() -> Body:
    now = utcnow()
    with session_scope() as db:
        by_status = dict(db.execute(select(User.status, func.count()).group_by(User.status)).tuples().all())
        by_plan = dict(db.execute(select(User.plan, func.count()).group_by(User.plan)).tuples().all())
        uploads_24h = db.scalar(
            select(func.count()).select_from(UsageEvent).where(UsageEvent.created_at > now - accounts.QUOTA_WINDOW)
        )
        revenue = db.scalar(select(func.sum(Payment.amount)).where(Payment.status == "COMPLETED")) or 0
        active_subscriptions = db.scalar(
            select(func.count()).select_from(Subscription).where(Subscription.status == "ACTIVE")
        )
    return {
        "active_subscriptions": active_subscriptions or 0,
        "users_by_status": by_status,
        "users_by_plan": by_plan,
        "uploads_24h": uploads_24h or 0,
        "revenue_usd": f"{revenue:.2f}",
    }, 200
