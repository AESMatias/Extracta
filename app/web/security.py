"""Request-level protections shared by every API route.

- ApiError: raise it anywhere in a route to answer with a JSON error.
- RateLimiter: fixed-window counters in Redis (login, registration, admin password).
- UploadLock: one upload at a time per user, so two parallel uploads cannot exceed the quota.
- same_origin(): state-changing requests must come from our own site (CSRF defense in depth,
  on top of SameSite=Lax cookies).
- current_user() / require_user(): the signed-in account behind the session cookie.
"""

import uuid
from typing import Any
from urllib.parse import urlsplit

from flask import current_app, request, session
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User

USER_KEY = "user_id"


class ApiError(Exception):
    def __init__(self, status: int, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.extra = extra

    def body(self) -> dict[str, Any]:
        return {"error": self.message, **self.extra}


def settings() -> Settings:
    value: Settings = current_app.extensions["settings"]
    return value


def client_ip() -> str:
    # ProxyFix (see create_app) has already replaced remote_addr with the client behind Nginx.
    return request.remote_addr or "unknown"


class RateLimiter:
    def __init__(self, client: Any) -> None:
        self._client = client

    def hit(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Count one attempt; False once the key went over `limit` in the current window."""
        name = f"ratelimit:{key}"
        pipe = self._client.pipeline()
        pipe.incr(name)
        pipe.expire(name, window_seconds, nx=True)  # the window starts at the first attempt
        count, _ = pipe.execute()
        return int(count) <= limit


def rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    limiter: RateLimiter = current_app.extensions["rate_limiter"]
    if not limiter.hit(key, limit=limit, window_seconds=window_seconds):
        raise ApiError(429, "Too many attempts. Wait a few minutes and try again.")


class UploadLock:
    def __init__(self, client: Any, *, ttl_seconds: int = 900) -> None:
        self._client = client
        self._ttl = ttl_seconds

    def acquire(self, user_id: uuid.UUID) -> bool:
        return bool(self._client.set(f"upload-lock:{user_id}", "1", nx=True, ex=self._ttl))

    def release(self, user_id: uuid.UUID) -> None:
        self._client.delete(f"upload-lock:{user_id}")


def same_origin() -> bool:
    """True unless the browser says the request comes from another site."""
    origin = request.headers.get("Origin")
    if origin is None or request.method in ("GET", "HEAD", "OPTIONS"):
        return True  # non-browser clients and safe methods
    if origin.rstrip("/") == settings().public_base_url:
        return True
    return urlsplit(origin).netloc == request.host  # same host, e.g. reached through another address


def current_user(db: Session) -> User | None:
    raw = session.get(USER_KEY)
    if not raw:
        return None
    try:
        user = db.get(User, uuid.UUID(raw))
    except ValueError:
        user = None
    if user is None or user.status in ("rejected", "suspended"):
        session.pop(USER_KEY, None)  # deleted or blocked since the cookie was issued
        return None
    return user


def require_user(db: Session) -> User:
    user = current_user(db)
    if user is None:
        raise ApiError(401, "Sign in to continue.")
    return user


def require_active(user: User) -> None:
    if user.status == "pending":
        raise ApiError(403, "Your account is waiting for approval by the administrator.")


def sign_in(user: User) -> None:
    session.clear()  # drop anything from a previous account
    session[USER_KEY] = str(user.id)
    session.permanent = True
