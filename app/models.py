"""Database tables.

- users: accounts (email + password and/or Google), status, plan and privileges.
- usage_events: one row per accepted upload, for the rolling 24-hour quota.
- payments: PayPal captures that bought a plan.
- documents: results of persistent-mode tasks only. Task status lives in Celery's Redis result
  backend for both modes, so this table only ever holds completed extractions.

The schema is created by Alembic migrations (app/migrations); keep both in sync.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self

from sqlalchemy import JSON, BigInteger, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime, utcnow
from app.schemas import DocumentSchema

UserStatus = Literal["pending", "active", "rejected", "suspended"]
USER_STATUSES = ("pending", "active", "rejected", "suspended")
PLAN_IDS = ("free", "starter", "pro", "business", "ultra")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("status", USER_STATUSES), name="ck_users_status"),
        CheckConstraint(_in("plan", PLAN_IDS), name="ck_users_plan"),
        CheckConstraint("daily_limit_override IS NULL OR daily_limit_override >= 0", name="ck_users_daily_limit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # always stored lowercase
    name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # None for Google-only accounts
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    plan: Mapped[str] = mapped_column(String(16), default="free")
    plan_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # None: no expiry
    daily_limit_override: Mapped[int | None] = mapped_column(Integer)  # set by the admin, beats the plan
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[uuid.UUID]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16), default="paypal")
    provider_order_id: Mapped[str] = mapped_column(String(64), unique=True)  # makes captures idempotent
    plan: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # same UUID as the Celery task
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str | None] = mapped_column(String(8))
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))  # full DocumentSchema
    llm_provider: Mapped[str] = mapped_column(String(32))
    llm_model: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)

    @classmethod
    def from_extraction(
        cls,
        *,
        task_id: uuid.UUID,
        filename: str,
        extraction: DocumentSchema,
        llm_provider: str,
        llm_model: str,
        user_id: uuid.UUID | None = None,
    ) -> Self:
        return cls(
            id=task_id,
            user_id=user_id,
            filename=filename,
            document_type=extraction.document_type.value,
            language=extraction.language,
            title=extraction.title,
            summary=extraction.summary,
            data=extraction.model_dump(mode="json"),  # mode="json": dates become "YYYY-MM-DD" strings
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
