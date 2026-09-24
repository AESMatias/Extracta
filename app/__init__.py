"""Flask application factory.

Gunicorn builds the app by calling `create_app()` (see docker-compose.yml).
Tests call `create_app(settings)` with their own settings, so every test gets
a fresh, isolated app instead of sharing one global object.
"""

from flask import Flask

from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)

    # Keep the validated settings on the app so any part of it can reach them.
    app.extensions["settings"] = settings or get_settings()

    @app.get("/health")
    def health() -> dict[str, str]:
        # Liveness probe: answers as long as the web process is up.
        return {"status": "ok"}

    return app
