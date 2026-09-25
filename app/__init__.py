"""Flask application factory: the JSON API behind the Next.js frontend.

Gunicorn builds the app by calling `create_app()` (see docker-compose.yml). Tests call
`create_app(settings, ...)` with their own settings and fakes, so every test gets a fresh,
isolated app instead of sharing one global object.
"""

from datetime import timedelta
from typing import Any

import redis
from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import Settings, get_settings
from app.web.admin_routes import admin
from app.web.auth_routes import auth
from app.web.billing_routes import billing
from app.web.google import GoogleOAuth
from app.web.ownership import RedisTaskOwnership, TaskOwnership
from app.web.paypal import PayPalClient
from app.web.queue import CeleryTaskQueue, TaskQueue
from app.web.routes import MAX_FILES_PER_UPLOAD, api
from app.web.security import ApiError, RateLimiter, UploadLock, same_origin

SESSION_LIFETIME = timedelta(days=14)


def create_app(
    settings: Settings | None = None,
    *,
    task_queue: TaskQueue | None = None,
    ownership: TaskOwnership | None = None,
    redis_client: Any = None,
    google: GoogleOAuth | None = None,
    paypal: PayPalClient | None = None,
) -> Flask:
    app = Flask(__name__)

    # Keep the validated settings on the app so any part of it can reach them.
    app.extensions["settings"] = settings or get_settings()  # get_settings() is cached: .env is read once per process
    settings = app.extensions["settings"]

    app.config.update(
        SECRET_KEY=settings.secret_key.get_secret_value(),  # signs the session cookie
        SESSION_COOKIE_HTTPONLY=True,  # JavaScript cannot read the cookie
        SESSION_COOKIE_SAMESITE="Lax",  # other sites cannot make the browser send it on a POST (CSRF)
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,  # HTTPS only, in production
        PERMANENT_SESSION_LIFETIME=SESSION_LIFETIME,
        # Hard cap on a whole upload request; each file is also checked against its plan's size.
        MAX_CONTENT_LENGTH=MAX_FILES_PER_UPLOAD * settings.max_upload_bytes + 1024 * 1024,
    )
    if settings.trusted_proxies:
        # Behind Nginx: trust its X-Forwarded-* headers for the client IP, scheme and host.
        hops = settings.trusted_proxies
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)  # type: ignore[method-assign]

    client = redis_client or redis.Redis.from_url(settings.celery_result_backend)  # connects lazily
    app.extensions["task_queue"] = task_queue or CeleryTaskQueue()
    app.extensions["task_ownership"] = ownership or RedisTaskOwnership(client, ttl_seconds=settings.result_ttl_seconds)
    app.extensions["rate_limiter"] = RateLimiter(client)
    app.extensions["upload_lock"] = UploadLock(client)
    if google is None and settings.google_client_id and settings.google_client_secret:
        google = GoogleOAuth(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret.get_secret_value(),
            redirect_uri=f"{settings.public_base_url}/api/auth/google/callback",
        )
    app.extensions["google"] = google
    if paypal is None and settings.paypal_client_id and settings.paypal_client_secret:
        paypal = PayPalClient(
            client_id=settings.paypal_client_id,
            client_secret=settings.paypal_client_secret.get_secret_value(),
            env=settings.paypal_env,
            currency="USD",  # plan prices are in USD
        )
    app.extensions["paypal"] = paypal

    for blueprint in (api, auth, admin, billing):
        app.register_blueprint(blueprint)

    @app.before_request
    def reject_cross_site_requests() -> tuple[dict[str, str], int] | None:
        if not same_origin():
            return {"error": "Cross-site request refused."}, 403
        return None

    @app.errorhandler(ApiError)
    def api_error(exc: ApiError) -> tuple[dict[str, Any], int]:
        return exc.body(), exc.status

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException) -> tuple[dict[str, Any], int]:
        messages = {413: "The upload is too large. Send fewer or smaller files."}
        code = exc.code or 500
        return {"error": messages.get(code, exc.description or exc.name)}, code

    @app.after_request
    def security_headers(response: Response) -> Response:
        # The API only returns JSON and files: nothing in it may run as a page or inside a frame.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")  # account data is never cached
        return response

    return app
