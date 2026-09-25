"""Account rules: registration, password and Google sign-in, email verification, passwords,
plans and the rolling 24-hour quota.

Framework-free: routes call these functions with an open SQLAlchemy session.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import utcnow
from app.models import Subscription, UsageEvent, User
from app.plans import Plan, effective_plan

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
QUOTA_WINDOW = timedelta(hours=24)
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
    used: int
    limit: int
    next_slot_at: datetime | None  # when the oldest upload in the window stops counting

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)


def normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    if len(email) > 320 or not _EMAIL.match(email):
        raise AccountError("Enter a valid email address.")
    return email


def _clean_name(name: str | None) -> str | None:
    name = " ".join((name or "").split())[:120]
    return name or None


def validate_password(password: str, email: str) -> None:
    if not PASSWORD_MIN_LENGTH <= len(password or "") <= PASSWORD_MAX_LENGTH:
        raise AccountError(f"Use a password between {PASSWORD_MIN_LENGTH} and {PASSWORD_MAX_LENGTH} characters.")
    if password.strip().lower() == email:
        raise AccountError("The password cannot be your email address.")


def ensure_can_sign_in(user: User) -> None:
    if user.status == "rejected":
        raise AccountBlockedError("This account request was rejected.")
    if user.status == "suspended":
        raise AccountBlockedError("This account is suspended. Contact the administrator.")


def register(db: Session, *, email: str, password: str, name: str | None, require_approval: bool) -> User:
    email = normalize_email(email)
    validate_password(password, email)
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
    validate_password(password, user.email)
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


def daily_limit(user: User, now: datetime) -> int:
    if user.daily_limit_override is not None:
        return user.daily_limit_override
    return current_plan(user, now).docs_per_24h


def usage(db: Session, user: User, now: datetime) -> Usage:
    times = (
        db.execute(
            select(UsageEvent.created_at)
            .where(UsageEvent.user_id == user.id, UsageEvent.created_at > now - QUOTA_WINDOW)
            .order_by(UsageEvent.created_at)
        )
        .scalars()
        .all()
    )
    return Usage(used=len(times), limit=daily_limit(user, now), next_slot_at=times[0] + QUOTA_WINDOW if times else None)


def record_usage(db: Session, user_id: uuid.UUID, task_ids: list[str], now: datetime) -> None:
    db.add_all(UsageEvent(user_id=user_id, task_id=uuid.UUID(task_id), created_at=now) for task_id in task_ids)


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
        "daily_limit": daily_limit(user, now),
        "created_at": user.created_at.isoformat(),
    }
    if quota is not None:
        data["usage"] = {
            "used": quota.used,
            "limit": quota.limit,
            "remaining": quota.remaining,
            "next_slot_at": quota.next_slot_at.isoformat() if quota.next_slot_at else None,
        }
    return data
