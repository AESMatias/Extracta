from pathlib import Path

import pytest
from pydantic import SecretStr

from app import create_app
from app.config import Settings, get_settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        gemini_api_key=SecretStr("test-gemini-key"),
        database_url=SecretStr("postgresql+psycopg://user:secret@db.example.com:5432/app"),
        secret_key=SecretStr("k" * 32),
    )


def test_health_returns_ok(settings: Settings) -> None:
    client = create_app(settings).test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_unknown_route_returns_404(settings: Settings) -> None:
    client = create_app(settings).test_client()

    assert client.get("/does-not-exist").status_code == 404


def test_settings_are_attached_to_the_app(settings: Settings) -> None:
    app = create_app(settings)

    assert app.extensions["settings"] is settings


def test_each_call_builds_an_independent_app(settings: Settings) -> None:
    assert create_app(settings) is not create_app(settings)


def test_without_arguments_uses_environment_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # This is how gunicorn calls it: create_app() with no arguments.
    monkeypatch.chdir(tmp_path)  # no real .env file here
    monkeypatch.setenv("GEMINI_API_KEY", "env-gemini-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("SECRET_KEY", "k" * 32)
    get_settings.cache_clear()

    try:
        app = create_app()
        assert app.extensions["settings"] is get_settings()
    finally:
        get_settings.cache_clear()


def test_optional_integrations_are_wired_only_when_configured(settings: Settings) -> None:
    plain = create_app(settings)
    settings.google_client_id = "id.apps.googleusercontent.com"
    settings.google_client_secret = SecretStr("google-secret")
    settings.paypal_client_id = "paypal-id"
    settings.paypal_client_secret = SecretStr("paypal-secret")
    full = create_app(settings)

    assert plain.extensions["google"] is None and plain.extensions["paypal"] is None
    assert full.extensions["google"].redirect_uri == "http://localhost:8080/api/auth/google/callback"
    assert full.extensions["paypal"].env == "sandbox"
