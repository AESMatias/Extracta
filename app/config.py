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

    # Signs the session cookie that ties each browser to its own tasks. Generate with:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: SecretStr = Field(min_length=32)
    session_cookie_secure: bool = False  # set to true in production (HTTPS only)

    upload_dir: Path = Path("/tmp_uploads")
    max_upload_mb: int = Field(default=50, gt=0)  # hard cap for every plan
    # Files still on disk after this many hours were orphaned (e.g. a worker killed mid-task).
    orphan_max_age_hours: int = Field(default=6, gt=0)

    # Public URL of the site, as users type it. Used for the Google callback and to reject
    # cross-site requests (Origin check).
    public_base_url: str = "http://localhost:8080"
    trusted_proxies: int = Field(default=1, ge=0)  # reverse proxies in front of Flask (Nginx)

    # Accounts
    require_manual_approval: bool = False  # true: new accounts wait in "pending" until approved
    # Password for /admin. Admin is disabled while it is empty.
    admin_password: SecretStr | None = Field(default=None, min_length=12)
    google_client_id: str | None = None  # Google sign-in is enabled when both are set
    google_client_secret: SecretStr | None = None

    # PayPal checkout (30-day plan passes). Payments are enabled when both credentials are set.
    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None
    paypal_env: Literal["sandbox", "live"] = "sandbox"  # prices are in USD (app/plans.py)

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

    @field_validator("public_base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def paypal_enabled(self) -> bool:
        return bool(self.paypal_client_id and self.paypal_client_secret)

    @property
    def admin_enabled(self) -> bool:
        return self.admin_password is not None


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, built once on first use.

    So .env is read and validated only once, not in every request.
    """
    return Settings()
