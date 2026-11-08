"""Request-level protections shared by every API route.

- ApiError: raise it anywhere in a route to answer with a JSON error.
- RateLimiter: fixed-window counters in Redis (login, registration, admin password).
- assess_login_risk(): 3-layer pre-hash login defense (sub-millisecond risk score, known-device
  session marker, and stateless HMAC-SHA256 Proof-of-Work challenge before touching PostgreSQL or
  PBKDF2-SHA256).
- UploadLock: one upload at a time per user, so two parallel uploads cannot exceed the quota.
- same_origin(): state-changing requests must come from our own site (CSRF defense in depth,
  on top of SameSite=Lax cookies).
- current_user() / require_user(): the signed-in account behind the session cookie. The cookie
  also carries a fingerprint of the password: changing the password signs out every other session.
"""

import hashlib
import hmac
import re
import secrets
import time
import uuid
from typing import Any
from urllib.parse import urlsplit

from flask import current_app, request, session
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import User
from app.tokens import password_fingerprint

USER_KEY = "user_id"
PASSWORD_KEY = "pw"
KNOWN_DEVICE_KEY = "kd"
POW_DIFFICULTY_BITS = 15
POW_TTL_SECONDS = 180
_BOT_UA_RE = re.compile(
    r"curl/|wget/|python-requests|python-urllib|httpx/|aiohttp/|go-http-client|libwww-perl|"
    r"scrapy|nikto|sqlmap|masscan|zgrab|nmap|headlesschrome|phantomjs",
    re.IGNORECASE,
)


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


def _ipv4_subnet(ip: str) -> str:
    parts = ip.strip().split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return ip[:24]


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

    def count(self, key: str) -> int:
        raw = self._client.get(f"ratelimit:{key}")
        return int(raw) if raw is not None else 0


def rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    limiter: RateLimiter = current_app.extensions["rate_limiter"]
    if not limiter.hit(key, limit=limit, window_seconds=window_seconds):
        raise ApiError(429, "Too many attempts. Wait a few minutes and try again.")


def is_known_device() -> bool:
    return bool(session.get(KNOWN_DEVICE_KEY))


def mark_known_device() -> None:
    session[KNOWN_DEVICE_KEY] = True
    session.permanent = True


def _pow_context(ip: str, ua: str) -> str:
    return hashlib.sha256(f"{ip}|{(ua or '')[:120]}".encode()).hexdigest()[:16]


def _has_leading_zero_bits(digest: bytes, bits: int) -> bool:
    full_bytes = bits // 8
    rem_bits = bits % 8
    for idx in range(full_bytes):
        if digest[idx] != 0:
            return False
    if rem_bits > 0:
        mask = (0xFF << (8 - rem_bits)) & 0xFF
        if (digest[full_bytes] & mask) != 0:
            return False
    return True


def create_pow_challenge(secret: str, ip: str, ua: str, bits: int = POW_DIFFICULTY_BITS) -> str:
    payload = f"v1.{int(time.time())}.{bits}.{secrets.token_hex(8)}"
    ctx = _pow_context(ip, ua)
    mac = hmac.new(secret.encode(), f"pow:{payload}:{ctx}".encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{mac}"


def verify_pow_solution(secret: str, challenge: str | None, nonce: str | None, ip: str, ua: str) -> bool:
    if not challenge or not nonce or len(challenge) > 256 or len(nonce) > 64:
        return False
    parts = challenge.split(".")
    if len(parts) != 5 or parts[0] != "v1":
        return False
    _, ts_raw, bits_raw, rand_hex, sig = parts
    try:
        ts = int(ts_raw)
        bits = int(bits_raw)
    except ValueError:
        return False
    age = int(time.time()) - ts
    if age < -5 or age > POW_TTL_SECONDS or bits < 10 or bits > 24:
        return False
    payload = f"v1.{ts_raw}.{bits_raw}.{rand_hex}"
    ctx = _pow_context(ip, ua)
    expected = hmac.new(secret.encode(), f"pow:{payload}:{ctx}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    digest = hashlib.sha256(f"{challenge}:{nonce}".encode()).digest()
    return _has_leading_zero_bits(digest, bits)


def assess_login_risk(
    *,
    ip_key: str,
    ip_limit: int,
    target_key: str | None = None,
    target_limit: int = 10,
    window_seconds: int = 900,
    pow_challenge: str | None = None,
    pow_nonce: str | None = None,
) -> None:
    """Layer 1 & 2 pre-hash defense (~0.1 ms): score the client before touching PostgreSQL or PBKDF2."""
    ip = client_ip()
    ua = request.headers.get("User-Agent", "")
    secret = settings().secret_key.get_secret_value()
    known = is_known_device()
    pow_ok = verify_pow_solution(secret, pow_challenge, pow_nonce, ip, ua)

    # 1. Automated scraper / CLI User-Agent -> drop immediately before touching Redis or DB.
    if _BOT_UA_RE.search(ua):
        raise ApiError(429, "Too many attempts. Wait a few minutes and try again.")

    # 2. Per-IP hard rate limit (always enforced per source IP).
    limiter: RateLimiter = current_app.extensions["rate_limiter"]
    if not limiter.hit(ip_key, limit=ip_limit, window_seconds=window_seconds):
        raise ApiError(429, "Too many attempts. Wait a few minutes and try again.")

    # 3. Subnet velocity & browser-header consistency score.
    score = 0
    subnet_key = f"login-subnet:{_ipv4_subnet(ip)}"
    subnet_ok = limiter.hit(subnet_key, limit=60, window_seconds=window_seconds)
    if not subnet_ok or limiter.count(subnet_key) > 30:
        score += 40

    if (
        "mozilla/5.0" in ua.lower()
        and not request.headers.get("Accept-Language")
        and not request.headers.get("Sec-Fetch-Site")
        and not request.headers.get("Sec-CH-UA")
    ):
        score += 40

    # 4. Per-account surge: never globally lock out a known device or a browser that solved PoW.
    if (
        target_key is not None
        and not limiter.hit(target_key, limit=target_limit, window_seconds=window_seconds)
        and not known
        and not pow_ok
    ):
        raise ApiError(
            429,
            "Too many attempts. Wait a few minutes and try again.",
            challenge_required=True,
            pow_challenge=create_pow_challenge(secret, ip, ua),
        )

    if score >= 35 and not known and not pow_ok:
        raise ApiError(
            429,
            "Security verification required. Please try again.",
            challenge_required=True,
            pow_challenge=create_pow_challenge(secret, ip, ua),
        )


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
    stale = user is None or session.get(PASSWORD_KEY) != password_fingerprint(user)
    if stale or user is None or user.status in ("rejected", "suspended", "deleted"):
        # Deleted, blocked, or the password changed since the cookie was issued.
        session.pop(USER_KEY, None)
        session.pop(PASSWORD_KEY, None)
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


def require_verified(user: User) -> None:
    if settings().require_email_verification and user.email_verified_at is None:
        raise ApiError(403, "Confirm your email address first: open the link we sent you.", verify_email=True)


def sign_in(user: User) -> None:
    session.clear()  # drop anything from a previous account
    session[USER_KEY] = str(user.id)
    session[PASSWORD_KEY] = password_fingerprint(user)
    session[KNOWN_DEVICE_KEY] = True
    session.permanent = True
