"""Account endpoints: register, sign in (password or Google), sign out, current user."""

import hmac
from typing import Any

from flask import Blueprint, current_app, redirect, request, session
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers import Response

from app import accounts
from app.db import session_scope, utcnow
from app.web.google import GoogleAuthError, GoogleOAuth, new_code_verifier, new_state
from app.web.security import ApiError, client_ip, current_user, rate_limit, settings, sign_in

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
            body = accounts.serialize_user(user, now, accounts.usage(db, user, now))
            sign_in(user)
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
            body = accounts.serialize_user(user, now, accounts.usage(db, user, now))
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
    now = utcnow()
    with session_scope() as db:
        user = current_user(db)
        if user is None:
            raise ApiError(401, "Not signed in.")
        return {"user": accounts.serialize_user(user, now, accounts.usage(db, user, now))}, 200


@auth.get("/providers")
def providers() -> Body:
    config = settings()
    return {"google": config.google_enabled, "manual_approval": config.require_manual_approval}, 200


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
