"""Account endpoints: register, sign in (password or Google), sign out, current user, email
verification and passwords (forgot, reset, change).

Links in emails carry their token after "#", which browsers never send to a server: tokens do
not end up in Nginx's access log. The page reads it and posts it here.
"""

import hmac
from email.message import EmailMessage
from typing import Any

from flask import Blueprint, current_app, redirect, request, session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers import Response

from app import accounts, emails, tokens
from app.db import session_scope, utcnow
from app.mail import Mailer
from app.models import User
from app.web.google import GoogleAuthError, GoogleOAuth, new_code_verifier, new_state
from app.web.security import ApiError, client_ip, current_user, rate_limit, require_user, settings, sign_in

auth = Blueprint("auth", __name__, url_prefix="/api/auth")
Body = tuple[dict[str, Any], int]
_GOOGLE_KEY = "google_oauth"


def _json() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError(400, "Send a JSON body.")
    return payload


def _account_error(exc: accounts.AccountError) -> ApiError:
    return ApiError(exc.status_code, str(exc))


def _send(message: EmailMessage) -> None:
    mailer: Mailer = current_app.extensions["mailer"]
    mailer.send(message)


def _secret() -> str:
    return settings().secret_key.get_secret_value()


def _send_verification(user: User) -> None:
    config = settings()
    token = tokens.email_verification_token(_secret(), user)
    link = f"{config.public_base_url}/verify-email#token={token}"
    _send(emails.verify_email(sender=config.mail_from, to=user.email, name=user.name, link=link))


def _send_reset(user: User) -> None:
    config = settings()
    token = tokens.password_reset_token(_secret(), user)
    link = f"{config.public_base_url}/reset-password#token={token}"
    _send(emails.reset_password(sender=config.mail_from, to=user.email, name=user.name, link=link))


def _send_password_changed(user: User) -> None:
    config = settings()
    link = f"{config.public_base_url}/forgot-password"
    _send(emails.password_changed(sender=config.mail_from, to=user.email, name=user.name, reset_link=link))


@auth.post("/register")
def register() -> Body:
    rate_limit(f"register:{client_ip()}", limit=10, window_seconds=3600)
    data = _json()
    now = utcnow()
    try:
        with session_scope() as db:
            user = accounts.register(
                db,
                email=str(data.get("email", "")),
                password=str(data.get("password", "")),
                name=data.get("name"),
                require_approval=settings().require_manual_approval,
            )
            body = accounts.describe(db, user, now)
            sign_in(user)
            _send_verification(user)
    except accounts.AccountError as exc:
        raise _account_error(exc) from None
    except IntegrityError:  # two registrations with the same email at the same instant
        raise ApiError(409, "An account with this email already exists. Sign in instead.") from None
    return {"user": body}, 201


@auth.post("/login")
def login() -> Body:
    data = _json()
    email = str(data.get("email", "")).strip().lower()
    rate_limit(f"login-ip:{client_ip()}", limit=30, window_seconds=900)
    rate_limit(f"login-email:{email}", limit=10, window_seconds=900)  # slows password guessing per account
    now = utcnow()
    try:
        with session_scope() as db:
            user = accounts.authenticate(db, email=email, password=str(data.get("password", "")))
            body = accounts.describe(db, user, now)
            sign_in(user)
    except accounts.AccountError as exc:
        raise _account_error(exc) from None
    return {"user": body}, 200


@auth.post("/logout")
def logout() -> Body:
    session.clear()
    return {"ok": True}, 200


@auth.get("/me")
def me() -> Body:
    """The signed-in account, or null for visitors (200 either way: not being signed in is normal)."""
    now = utcnow()
    with session_scope() as db:
        user = current_user(db)
        if user is None:
            return {"user": None}, 200
        return {"user": accounts.describe(db, user, now)}, 200


@auth.get("/providers")
def providers() -> Body:
    config = settings()
    return {
        "google": config.google_enabled,
        "manual_approval": config.require_manual_approval,
        "email_verification": config.require_email_verification,
    }, 200


# --------------------------------------------------------------------------- email verification


@auth.post("/email/resend")
def resend_verification() -> Body:
    with session_scope() as db:
        user = require_user(db)
        if accounts.is_verified(user):
            return {"sent": False, "already_verified": True}, 200
        rate_limit(f"verify-resend:{user.id}", limit=3, window_seconds=3600)
        _send_verification(user)
    return {"sent": True}, 200


@auth.post("/email/verify")
def verify_email() -> Body:
    rate_limit(f"verify:{client_ip()}", limit=30, window_seconds=3600)
    token = str(_json().get("token", ""))
    try:
        user_id, email = tokens.read_email_verification_token(_secret(), token)
    except tokens.InvalidTokenError as exc:
        raise ApiError(400, str(exc)) from None
    with session_scope() as db:
        user = db.get(User, user_id)
        if user is None or user.email != email:
            raise ApiError(400, "This link is invalid or has expired.")
        accounts.mark_email_verified(user, utcnow())
    return {"verified": True}, 200


# --------------------------------------------------------------------------- passwords


@auth.post("/password/forgot")
def forgot_password() -> Body:
    """Always the same answer, so it cannot be used to find out which emails have an account."""
    rate_limit(f"forgot-ip:{client_ip()}", limit=10, window_seconds=3600)
    raw_email = str(_json().get("email", ""))
    try:
        email = accounts.normalize_email(raw_email)
    except accounts.AccountError:
        return {"ok": True}, 200
    rate_limit(f"forgot-email:{email}", limit=5, window_seconds=3600)
    with session_scope() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.status not in ("rejected", "suspended"):
            _send_reset(user)
    return {"ok": True}, 200


@auth.post("/password/reset")
def reset_password() -> Body:
    rate_limit(f"reset:{client_ip()}", limit=20, window_seconds=3600)
    data = _json()
    try:
        user_id, fingerprint = tokens.read_password_reset_token(_secret(), str(data.get("token", "")))
    except tokens.InvalidTokenError as exc:
        raise ApiError(400, str(exc)) from None
    now = utcnow()
    try:
        with session_scope() as db:
            user = db.get(User, user_id)
            if user is None or not hmac.compare_digest(fingerprint, tokens.password_fingerprint(user)):
                raise ApiError(400, "This link is invalid, expired or was already used. Ask for a new one.")
            accounts.ensure_can_sign_in(user)
            accounts.set_password(user, str(data.get("password", "")))
            accounts.mark_email_verified(user, now)  # the link reached the inbox: the email is theirs
            user.last_login_at = now
            db.flush()
            body = accounts.describe(db, user, now)
            sign_in(user)
            _send_password_changed(user)
    except accounts.AccountError as exc:
        raise _account_error(exc) from None
    return {"user": body}, 200


@auth.post("/password/change")
def change_password() -> Body:
    data = _json()
    now = utcnow()
    try:
        with session_scope() as db:
            user = require_user(db)
            rate_limit(f"password-change:{user.id}", limit=10, window_seconds=900)
            accounts.change_password(
                user,
                current_password=str(data.get("current_password") or ""),
                new_password=str(data.get("new_password", "")),
            )
            db.flush()
            body = accounts.describe(db, user, now)
            sign_in(user)  # this session stays signed in; every other one is signed out
            _send_password_changed(user)
    except accounts.AccountError as exc:
        raise _account_error(exc) from None
    return {"user": body}, 200


# --------------------------------------------------------------------------- Google


def _google() -> GoogleOAuth:
    client: GoogleOAuth | None = current_app.extensions.get("google")
    if client is None:
        raise ApiError(404, "Google sign-in is not configured.")
    return client


def _back_to_site(path: str) -> Response:
    return redirect(f"{settings().public_base_url}{path}", code=302)


@auth.get("/google/login")
def google_login() -> Response:
    client = _google()
    state, verifier = new_state(), new_code_verifier()
    session[_GOOGLE_KEY] = {"state": state, "verifier": verifier}
    return redirect(client.authorization_url(state=state, code_verifier=verifier), code=302)


@auth.get("/google/callback")
def google_callback() -> Response:
    client = _google()
    pending = session.pop(_GOOGLE_KEY, None) or {}
    state = request.args.get("state", "")
    if request.args.get("error") or not pending or not hmac.compare_digest(state, pending.get("state", "")):
        return _back_to_site("/login?error=google_cancelled")
    try:
        profile = client.fetch_profile(code=request.args.get("code", ""), code_verifier=pending["verifier"])
        with session_scope() as db:
            user = accounts.google_sign_in(
                db,
                sub=profile.sub,
                email=profile.email,
                email_verified=profile.email_verified,
                name=profile.name,
                require_approval=settings().require_manual_approval,
            )
            sign_in(user)
    except accounts.AccountBlockedError:
        return _back_to_site("/login?error=account_blocked")
    except (GoogleAuthError, accounts.AccountError):
        return _back_to_site("/login?error=google_failed")
    return _back_to_site("/app")
