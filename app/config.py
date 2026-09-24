"""Application settings, loaded and validated from environment variables.

Docker Compose injects the variables from `.env`; locally, `.env` is also read
directly. Any missing or invalid value fails fast at startup instead of in the
middle of processing a document.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["gemini", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Treat "KEY=" (empty value, as in .env.sample) as not set.
        env_ignore_empty=True,
        extra="ignore",
    )

    # LLM provider and model, switchable without code changes.
    llm_provider: LLMProvider = "gemini"
    llm_model: str = "gemini-3.1-flash-lite"
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # SecretStr hides the password if the settings are ever logged or printed.
    database_url: SecretStr
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"  # task results live apart from the queue
    result_ttl_seconds: int = Field(default=3600, gt=0)  # how long results stay in Redis (ephemeral mode)

    upload_dir: Path = Path("/tmp_uploads")
    max_upload_mb: int = Field(default=50, gt=0)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg3_driver(cls, value: object) -> object:
        # Supabase shows "postgresql://..."; SQLAlchemy needs "postgresql+psycopg://..." for psycopg 3.
        if isinstance(value, str):
            for prefix in ("postgresql://", "postgres://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @model_validator(mode="after")
    def require_key_for_selected_provider(self) -> Self:
        keys = {"gemini": self.gemini_api_key, "openai": self.openai_api_key}
        key = keys[self.llm_provider]
        if key is None or not key.get_secret_value().strip():
            env_name = f"{self.llm_provider.upper()}_API_KEY"
            raise ValueError(f"{env_name} is required when LLM_PROVIDER={self.llm_provider}")
        return self

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once on first use.

    So .env is read and validated only once, not in every request.
    """
    return Settings()
