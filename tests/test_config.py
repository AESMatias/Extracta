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


def load() -> Settings:
    # _env_file=None: never read the real .env file during tests.
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_loads_defaults_with_minimal_valid_env(valid_env: None) -> None:
    settings = load()

    assert settings.llm_provider == "gemini"
    assert settings.llm_model == "gemini-3.1-flash-lite"
    assert settings.celery_broker_url == "redis://redis:6379/0"
    assert settings.upload_dir == Path("/tmp_uploads")
    assert settings.max_upload_mb == 50
    assert settings.max_upload_bytes == 50 * 1024 * 1024


def test_gemini_provider_requires_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")

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
    assert "secret" not in text


def test_get_settings_builds_once(valid_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Run from an empty dir so no real .env file is picked up.
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()

    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
