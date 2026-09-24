"""Flask application factory.

Gunicorn builds the app by calling `create_app()` (see docker-compose.yml).
Tests call `create_app(settings, ...)` with their own settings and fakes, so every test gets
a fresh, isolated app instead of sharing one global object.
"""

from flask import Flask

from app.config import Settings, get_settings
from app.web.ownership import RedisTaskOwnership, TaskOwnership
from app.web.queue import CeleryTaskQueue, TaskQueue
from app.web.routes import MAX_FILES_PER_UPLOAD, api


def create_app(
    settings: Settings | None = None,
    *,
    task_queue: TaskQueue | None = None,
    ownership: TaskOwnership | None = None,
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
        # Hard cap on a whole upload request; each file is also checked against MAX_UPLOAD_MB.
        MAX_CONTENT_LENGTH=MAX_FILES_PER_UPLOAD * settings.max_upload_bytes + 1024 * 1024,
    )
    app.extensions["task_queue"] = task_queue or CeleryTaskQueue()
    app.extensions["task_ownership"] = ownership or RedisTaskOwnership.from_url(
        settings.celery_result_backend, ttl_seconds=settings.result_ttl_seconds
    )
    app.register_blueprint(api)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
