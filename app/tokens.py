"""Signed, time-limited tokens for the links sent by email. No database table is needed.

- Email verification: names the account and the address; valid for 3 days.
- Password reset: names the account and a fingerprint of its current password hash; valid for
  1 hour. Once the password changes the fingerprint no longer matches, so each link works once.
- Account deletion: names the account and the address; valid for 48 hours. Once the account is
  deleted its email changes, so the link cannot be used again.

itsdangerous ships with Flask (it also signs Flask's session cookie).
"""

import hashlib
import uuid
from datetime import timedelta
from typing import Any

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.models import User

VERIFY_EMAIL_MAX_AGE = timedelta(days=3)
RESET_PASSWORD_MAX_AGE = timedelta(hours=1)
DELETE_ACCOUNT_MAX_AGE = timedelta(hours=48)
_VERIFY_SALT = "extracta.verify-email"
_RESET_SALT = "extracta.reset-password"
_DELETE_SALT = "extracta.delete-account"


class InvalidTokenError(ValueError):
    """The link is malformed, tampered with, expired or already used."""


def password_fingerprint(user: User) -> str:
    """Changes whenever the password changes (also from "no password" to one)."""
    return hashlib.sha256((user.password_hash or "").encode()).hexdigest()[:16]


def _serializer(secret: str, salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=salt)


def _load(secret: str, salt: str, token: str, max_age: timedelta) -> dict[str, Any]:
    try:
        data = _serializer(secret, salt).loads(token, max_age=int(max_age.total_seconds()))
    except BadSignature:  # also covers SignatureExpired
        raise InvalidTokenError("This link is invalid or has expired.") from None
    if not isinstance(data, dict):
        raise InvalidTokenError("This link is invalid or has expired.")
    return data


def _user_id(data: dict[str, Any]) -> uuid.UUID:
    try:
        return uuid.UUID(str(data.get("u")))
    except ValueError:
        raise InvalidTokenError("This link is invalid or has expired.") from None


def email_verification_token(secret: str, user: User) -> str:
    return _serializer(secret, _VERIFY_SALT).dumps({"u": str(user.id), "e": user.email})


def read_email_verification_token(secret: str, token: str) -> tuple[uuid.UUID, str]:
    data = _load(secret, _VERIFY_SALT, token, VERIFY_EMAIL_MAX_AGE)
    return _user_id(data), str(data.get("e", ""))


def password_reset_token(secret: str, user: User) -> str:
    return _serializer(secret, _RESET_SALT).dumps({"u": str(user.id), "p": password_fingerprint(user)})


def read_password_reset_token(secret: str, token: str) -> tuple[uuid.UUID, str]:
    data = _load(secret, _RESET_SALT, token, RESET_PASSWORD_MAX_AGE)
    return _user_id(data), str(data.get("p", ""))


def account_deletion_token(secret: str, user: User) -> str:
    return _serializer(secret, _DELETE_SALT).dumps({"u": str(user.id), "e": user.email})


def read_account_deletion_token(secret: str, token: str) -> tuple[uuid.UUID, str]:
    data = _load(secret, _DELETE_SALT, token, DELETE_ACCOUNT_MAX_AGE)
    return _user_id(data), str(data.get("e", ""))
