"""Administration: sign in with ADMIN_PASSWORD, review accounts, approve or reject them, and set
plans, expiry dates and custom daily limits. Every privilege a user has is listed explicitly.
Deletion requests from the public form are listed here too, so an account can be erased by hand
when the confirmation email never arrives.
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
from sqlalchemy.orm import Session

from app import accounts
from app.db import session_scope, utcnow
from app.models import DeletionRequest, Payment, Subscription, UsageEvent, User
from app.plans import PLANS
from app.schemas import summarize_validation_error
from app.web.auth_routes import erase_account
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
    pages_24h: int,
    paid_total: str,
    subscription: Subscription | None,
    now: datetime,
) -> dict[str, Any]:
    data = accounts.serialize_user(user, now)  # includes "privileges", with any admin override
    data.update(
        {
            "assigned_plan": user.plan,  # may differ from the effective plan when the pass expired
            "raw_plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "daily_limit_override": user.daily_limit_override,
            "uploads_24h": used_24h,
            "pages_24h": pages_24h,
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
        pages = accounts.pages_in_window(db, ids, now - accounts.QUOTA_WINDOW)
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
                u,
                recent.get(u.id, 0),
                totals.get(u.id, 0),
                pages.get(u.id, 0),
                f"{paid.get(u.id) or 0:.2f}",
                latest.get(u.id),
                now,
            )
            for u in users
        ]
    return {"users": items, "plans": [plan.to_dict() for plan in PLANS.values()]}, 200


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "active", "rejected", "suspended"] | None = None
    plan: Literal["free", "starter", "pro", "business", "ultra"] | None = None
    plan_expires_at: datetime | None = None  # ISO 8601 with timezone; null = no expiry
    daily_limit_override: int | None = Field(default=None, ge=0, le=1_000_000)  # pages per window; null = plan's
    page_credits: int | None = Field(default=None, ge=0, le=10_000_000)  # the prepaid page balance
    email_verified: bool | None = None  # true marks the address verified (e.g. confirmed by phone)


def _parse_id(value: str, missing: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError(404, missing) from None


@admin.patch("/users/<user_id>")
@admin_required
def update_user(user_id: str) -> Body:
    uid = _parse_id(user_id, "User not found.")
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
        for field in update.model_fields_set - {"email_verified", "page_credits"}:  # only what was sent; null clears
            setattr(user, field, getattr(update, field))
        if update.page_credits is not None:
            user.page_credits = update.page_credits
        if "email_verified" in update.model_fields_set:
            user.email_verified_at = (user.email_verified_at or now) if update.email_verified else None
        if user.plan == "free":
            user.plan_expires_at = None
        db.flush()
        pages = accounts.pages_in_window(db, [user.id], now - accounts.QUOTA_WINDOW).get(user.id, 0)
        subscription = accounts.current_subscription(db, user)
        return {"user": _admin_user(user, 0, 0, pages, "0.00", subscription, now)}, 200


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
        pages_24h = db.scalar(
            select(func.sum(UsageEvent.pages)).where(UsageEvent.created_at > now - accounts.QUOTA_WINDOW)
        )
        revenue = db.scalar(select(func.sum(Payment.amount)).where(Payment.status == "COMPLETED")) or 0
        active_subscriptions = db.scalar(
            select(func.count()).select_from(Subscription).where(Subscription.status == "ACTIVE")
        )
        pending_deletions = db.scalar(
            select(func.count()).select_from(DeletionRequest).where(DeletionRequest.status == "pending")
        )
    return {
        "active_subscriptions": active_subscriptions or 0,
        "pending_deletions": pending_deletions or 0,
        "users_by_status": by_status,
        "users_by_plan": by_plan,
        "uploads_24h": uploads_24h or 0,
        "pages_24h": int(pages_24h or 0),
        "revenue_usd": f"{revenue:.2f}",
    }, 200


# --------------------------------------------------------------------------- account deletion


@admin.post("/users/<user_id>/delete")
@admin_required
def delete_user(user_id: str) -> Body:
    """Erase an account by hand (e.g. its owner asked by email): same steps as self-service."""
    uid = _parse_id(user_id, "User not found.")
    with session_scope() as db:
        user = db.get(User, uid)
        if user is None or user.status == "deleted":
            raise ApiError(404, "User not found.")
        erase_account(db, user)
    return {"deleted": True}, 200


def _deletion_request(row: DeletionRequest, user: User) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "email": row.email,
        "name": user.name,
        "status": row.status,
        "account_status": user.status,
        "created_at": row.created_at.isoformat(),
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


@admin.get("/deletion-requests")
@admin_required
def list_deletion_requests() -> Body:
    with session_scope() as db:
        rows = db.execute(
            select(DeletionRequest, User)
            .join(User, User.id == DeletionRequest.user_id)
            .order_by((DeletionRequest.status == "pending").desc(), DeletionRequest.created_at.desc())
            .limit(500)
        ).tuples()
        return {"requests": [_deletion_request(row, user) for row, user in rows]}, 200


def _pending_request(db: Session, request_id: str) -> DeletionRequest:
    row = db.get(DeletionRequest, _parse_id(request_id, "Request not found."))
    if row is None:
        raise ApiError(404, "Request not found.")
    if row.status != "pending":
        raise ApiError(409, "This request was already handled.")
    return row


@admin.post("/deletion-requests/<request_id>/complete")
@admin_required
def complete_deletion_request(request_id: str) -> Body:
    """Erase the account behind a pending request (erase_account closes the request)."""
    with session_scope() as db:
        row = _pending_request(db, request_id)
        user = db.get(User, row.user_id)
        assert user is not None  # the foreign key cascades
        if user.status == "deleted":  # erased some other way meanwhile
            row.status, row.resolved_at = "completed", utcnow()
        else:
            erase_account(db, user)
        db.flush()
        return {"request": _deletion_request(row, user)}, 200


@admin.post("/deletion-requests/<request_id>/dismiss")
@admin_required
def dismiss_deletion_request(request_id: str) -> Body:
    """Close a request without erasing anything (e.g. the owner says they never sent it)."""
    with session_scope() as db:
        row = _pending_request(db, request_id)
        row.status, row.resolved_at = "dismissed", utcnow()
        user = db.get(User, row.user_id)
        assert user is not None
        db.flush()
        return {"request": _deletion_request(row, user)}, 200
