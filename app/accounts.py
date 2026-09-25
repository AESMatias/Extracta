"""Account rules: registration, password and Google sign-in, email verification, passwords,
plans and the page quota.

Quota: every plan allows some pages per rolling window (24 hours on Free, 30 days on paid plans).
Pages beyond that are paid from the prepaid balance (page packs). A PDF that fails to process
gives its pages back.

Framework-free: routes call these functions with an open SQLAlchemy session.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app import passwords
from app.db import utcnow
from app.models import Document, Subscription, UsageEvent, User
from app.plans import PREPAID_PRIVILEGES, Plan, effective_plan

PASSWORD_MIN_LENGTH = passwords.MIN_LENGTH
PASSWORD_MAX_LENGTH = passwords.MAX_LENGTH
QUOTA_WINDOW = timedelta(hours=24)  # the admin's "last 24 hours" figures
# PBKDF2-SHA256 with 600k iterations (OWASP 2023). scrypt would need ~32 MB of RAM per login.
HASH_METHOD = "pbkdf2:sha256:600000"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Checked when the email does not exist, so a missing account takes as long as a wrong password.
_DUMMY_HASH = generate_password_hash("timing-equalizer-not-a-real-password", method=HASH_METHOD)


class AccountError(ValueError):
    """A problem the user can fix; the message is safe to show."""

    status_code = 400


class EmailTakenError(AccountError):
    status_code = 409


class InvalidCredentialsError(AccountError):
    status_code = 401


class AccountBlockedError(AccountError):
    status_code = 403


@dataclass(frozen=True)
class Usage:
    used: int  # plan pages used in the current window
    limit: int  # plan pages per window
    window_hours: int
    next_slot_at: datetime | None  # when the oldest pages in the window start counting again
    credits: int = 0  # prepaid pages left

    @property
    def remaining(self) -> int:
        """Plan pages left in the window (prepaid pages not included)."""
        return max(self.limit - self.used, 0)

    @property
    def available(self) -> int:
        return self.remaining + self.credits


def normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 320 or not _EMAIL.match(email):
        raise AccountError("Enter a valid email address.")
    return email


def _clean_name(name: str | None) -> str | None:
    name = " ".join((name or "").split())[:120]
    return name or None


def validate_password(password: str, email: str, name: str | None = None) -> None:
    """NIST SP 800-63B policy: see app/passwords.py."""
    try:
        passwords.check(password, email=email, name=name)
    except passwords.WeakPasswordError as exc:
        raise AccountError(str(exc)) from None


def ensure_can_sign_in(user: User) -> None:
    if user.status == "rejected":
        raise AccountBlockedError("This account request was rejected.")
    if user.status == "suspended":
        raise AccountBlockedError("This account is suspended. Contact the administrator.")
    if user.status == "deleted":
        raise AccountBlockedError("This account was deleted.")


def register(db: Session, *, email: str, password: str, name: str | None, require_approval: bool) -> User:
    email = normalize_email(email)
    validate_password(password, email, _clean_name(name))
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailTakenError("An account with this email already exists. Sign in instead.")
    user = User(
        email=email,
        name=_clean_name(name),
        password_hash=generate_password_hash(password, method=HASH_METHOD),
        status="pending" if require_approval else "active",
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    try:
        email = normalize_email(email)
    except AccountError:
        email = ""
    user = db.scalar(select(User).where(User.email == email)) if email else None
    stored_hash = user.password_hash if user is not None and user.password_hash else _DUMMY_HASH
    password_ok = check_password_hash(stored_hash, password or "")
    if user is None or user.password_hash is None or not password_ok:
        raise InvalidCredentialsError("Incorrect email or password.")
    ensure_can_sign_in(user)
    user.last_login_at = utcnow()
    return user


def set_password(user: User, password: str) -> None:
    validate_password(password, user.email, user.name)
    user.password_hash = generate_password_hash(password, method=HASH_METHOD)


def change_password(user: User, *, current_password: str | None, new_password: str) -> None:
    """Accounts with a password must confirm it; Google-only accounts can add one."""
    if user.password_hash is not None and not check_password_hash(user.password_hash, current_password or ""):
        raise InvalidCredentialsError("Your current password is not correct.")
    set_password(user, new_password)


def is_verified(user: User) -> bool:
    return user.email_verified_at is not None


def mark_email_verified(user: User, now: datetime) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = now


def google_sign_in(
    db: Session, *, sub: str, email: str, email_verified: bool, name: str | None, require_approval: bool
) -> User:
    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        if not email_verified:
            raise AccountError("Your Google email address is not verified.")
        email = normalize_email(email)
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            # Google verified this email: link it to the existing account. If that account never
            # verified the address, whoever set its password may not own the inbox (someone can
            # register a victim's email first and wait): that password is removed.
            if user.email_verified_at is None:
                user.password_hash = None
            user.google_sub = sub
        else:
            user = User(
                email=email,
                name=_clean_name(name),
                google_sub=sub,
                status="pending" if require_approval else "active",
            )
            db.add(user)
    ensure_can_sign_in(user)
    mark_email_verified(user, utcnow())
    if not user.name:
        user.name = _clean_name(name)
    user.last_login_at = utcnow()
    db.flush()
    return user


def current_plan(user: User, now: datetime) -> Plan:
    return effective_plan(user.plan, user.plan_expires_at, now)


def page_limit(user: User, now: datetime) -> int:
    if user.daily_limit_override is not None:
        return user.daily_limit_override
    return current_plan(user, now).pages


def privileges(user: User, now: datetime) -> dict[str, Any]:
    """The plan's privileges, widened by what prepaid pages unlock while the balance is positive."""
    result = current_plan(user, now).privileges()
    result["pages"] = page_limit(user, now)
    if user.page_credits > 0:
        for key in ("max_pages_per_pdf", "max_file_mb", "max_files_per_upload"):
            result[key] = max(result[key], PREPAID_PRIVILEGES[key])
        result["can_save_to_db"] = True
    return result


def usage(db: Session, user: User, now: datetime) -> Usage:
    window = current_plan(user, now).window
    rows = db.execute(
        select(UsageEvent.created_at, UsageEvent.pages - UsageEvent.credits_used)
        .where(UsageEvent.user_id == user.id, UsageEvent.created_at > now - window)
        .order_by(UsageEvent.created_at)
    ).all()
    used = sum(int(plan_pages) for _, plan_pages in rows)
    first = next((created for created, plan_pages in rows if plan_pages > 0), None)
    return Usage(
        used=used,
        limit=page_limit(user, now),
        window_hours=int(window.total_seconds() // 3600),
        next_slot_at=first + window if first else None,
        credits=user.page_credits,
    )


@dataclass(frozen=True)
class Charge:
    task_id: str
    pages: int
    credits_used: int


def split_charge(pages: int, *, plan_left: int, credits_left: int) -> tuple[int, int] | None:
    """How many pages come from the plan and how many from prepaid pages; None if not enough."""
    from_plan = min(pages, plan_left)
    from_credits = pages - from_plan
    if from_credits > credits_left:
        return None
    return from_plan, from_credits


def record_usage(db: Session, user: User, charges: list[Charge], now: datetime) -> None:
    db.add_all(
        UsageEvent(
            user_id=user.id, task_id=uuid.UUID(c.task_id), pages=c.pages, credits_used=c.credits_used, created_at=now
        )
        for c in charges
    )
    spent = sum(c.credits_used for c in charges)
    if spent:
        user.page_credits = max(user.page_credits - spent, 0)


def refund_usage(db: Session, task_id: str) -> int:
    """A PDF that could not be processed gives its pages back. Returns the pages returned."""
    event = db.scalar(select(UsageEvent).where(UsageEvent.task_id == uuid.UUID(task_id)))
    if event is None:
        return 0
    if event.credits_used:
        user = db.get(User, event.user_id)
        if user is not None:
            user.page_credits += event.credits_used
    pages = event.pages
    db.delete(event)
    return pages


def pages_in_window(db: Session, user_ids: list[uuid.UUID], since: datetime) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(UsageEvent.user_id, func.sum(UsageEvent.pages))
        .where(UsageEvent.user_id.in_(user_ids), UsageEvent.created_at > since)
        .group_by(UsageEvent.user_id)
    ).tuples()
    return {user_id: int(total or 0) for user_id, total in rows}


def delete_account(db: Session, user: User, now: datetime) -> None:
    """Erase the account's personal data and documents.

    Payments stay (tax law requires keeping them), linked to a row with no personal data left:
    no email, name, password or Google link. The caller cancels any live subscription first.
    """
    db.execute(delete(Document).where(Document.user_id == user.id))
    db.execute(delete(UsageEvent).where(UsageEvent.user_id == user.id))
    user.email = f"deleted-{user.id}@deleted.invalid"
    user.name = None
    user.password_hash = None
    user.google_sub = None
    user.email_verified_at = None
    user.page_credits = 0
    user.plan = "free"
    user.plan_expires_at = None
    user.daily_limit_override = None
    user.status = "deleted"
    user.last_login_at = now
    db.flush()


def current_subscription(db: Session, user: User) -> Subscription | None:
    """The latest subscription the buyer approved (abandoned checkouts are ignored)."""
    return db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id, Subscription.status != "APPROVAL_PENDING")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )


def serialize_subscription(subscription: Subscription | None) -> dict[str, object] | None:
    if subscription is None:
        return None
    return {
        "id": subscription.provider_subscription_id,
        "plan": subscription.plan,
        "status": subscription.status,
        "next_billing_at": subscription.next_billing_at.isoformat() if subscription.next_billing_at else None,
        "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
    }


def describe(db: Session, user: User, now: datetime) -> dict[str, object]:
    """Everything the frontend shows about the signed-in account."""
    data = serialize_user(user, now, usage(db, user, now))
    data["subscription"] = serialize_subscription(current_subscription(db, user))
    return data


def serialize_user(user: User, now: datetime, quota: Usage | None = None) -> dict[str, object]:
    plan = current_plan(user, now)
    data: dict[str, object] = {
        "id": str(user.id),
        "email": user.email,
        "email_verified": is_verified(user),
        "name": user.name,
        "status": user.status,
        "plan": plan.to_dict(),
        "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at and plan.id != "free" else None,
        "has_password": user.password_hash is not None,
        "has_google": user.google_sub is not None,
        "page_limit": page_limit(user, now),
        "page_credits": user.page_credits,
        "privileges": privileges(user, now),
        "created_at": user.created_at.isoformat(),
    }
    if quota is not None:
        data["usage"] = {
            "used": quota.used,
            "limit": quota.limit,
            "remaining": quota.remaining,
            "credits": quota.credits,
            "available": quota.available,
            "window_hours": quota.window_hours,
            "next_slot_at": quota.next_slot_at.isoformat() if quota.next_slot_at else None,
        }
    return data
