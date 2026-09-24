from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings

ENV_VARS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "DATABASE_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "RESULT_TTL_SECONDS",
    "SECRET_KEY",
    "SESSION_COOKIE_SECURE",
    "UPLOAD_DIR",
    "MAX_UPLOAD_MB",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Isolate every test from the developer's real environment.
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@db.example.com:5432/app")
    monkeypatch.setenv("SECRET_KEY", "k" * 32)


def load() -> Settings:
    # _env_file=None: never read the real .env file during tests.
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_loads_defaults_with_minimal_valid_env(valid_env: None) -> None:
    settings = load()

    assert settings.llm_provider == "gemini"
    assert settings.llm_model == "gemini-3.1-flash-lite"
    assert settings.celery_broker_url == "redis://redis:6379/0"
    assert settings.celery_result_backend == "redis://redis:6379/1"  # results apart from the queue
    assert settings.result_ttl_seconds == 3600
    assert settings.session_cookie_secure is False  # True in production, behind HTTPS
    assert settings.upload_dir == Path("/tmp_uploads")
    assert settings.max_upload_mb == 50
    assert settings.max_upload_bytes == 50 * 1024 * 1024


def test_gemini_provider_requires_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("SECRET_KEY", "k" * 32)

    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        load()


def test_empty_key_counts_as_missing(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    # .env.sample ships "GEMINI_API_KEY=" with no value.
    monkeypatch.setenv("GEMINI_API_KEY", "")

    with pytest.raises(ValidationError, match="GEMINI_API_KEY"):
        load()


def test_openai_provider_requires_openai_key(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        load()


def test_openai_provider_with_key_loads(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "some-openai-model")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    settings = load()

    assert settings.llm_provider == "openai"
    assert settings.llm_model == "some-openai-model"


def test_unknown_provider_is_rejected(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    with pytest.raises(ValidationError, match="llm_provider"):
        load()


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("SECRET_KEY", "k" * 32)

    with pytest.raises(ValidationError, match="database_url"):
        load()


@pytest.mark.parametrize("value", ["0", "-5"])
def test_max_upload_mb_must_be_positive(valid_env: None, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("MAX_UPLOAD_MB", value)

    with pytest.raises(ValidationError, match="max_upload_mb"):
        load()


def test_secrets_are_not_exposed_in_repr(valid_env: None) -> None:
    text = repr(load())

    assert "test-gemini-key" not in text
    assert "secret@" not in text
    assert "k" * 32 not in text


def test_get_settings_builds_once(valid_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Run from an empty dir so no real .env file is picked up.
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()

    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql://user:secret@host:5432/db",  # as copied from the Supabase dashboard
        "postgres://user:secret@host:5432/db",
        "postgresql+psycopg://user:secret@host:5432/db",  # already explicit: unchanged
    ],
)
def test_database_url_uses_the_psycopg3_driver(valid_env: None, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("DATABASE_URL", raw)

    url = load().database_url.get_secret_value()

    assert url == "postgresql+psycopg://user:secret@host:5432/db"


@pytest.mark.parametrize("value", ["0", "-1"])
def test_result_ttl_must_be_positive(valid_env: None, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RESULT_TTL_SECONDS", value)

    with pytest.raises(ValidationError, match="result_ttl_seconds"):
        load()


def test_secret_key_is_required(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(ValidationError, match="secret_key"):
        load()


def test_secret_key_must_be_long(valid_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "too-short")

    with pytest.raises(ValidationError, match="secret_key"):
        load()
