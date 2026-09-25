"""Database tables.

- users: accounts (email + password and/or Google), status, plan and privileges.
- usage_events: one row per accepted PDF with the pages it used, for the rolling page quota.
- payments: money received through PayPal: page packs and subscription renewals.
- subscriptions: PayPal subscriptions that renew a plan every month.
- paypal_plans: the PayPal billing plan created for each Extracta plan and price.
- webhook_events: PayPal events already processed, so a redelivered event is applied once.
- documents: results of persistent-mode tasks only. Task status lives in Celery's Redis result
  backend for both modes, so this table only ever holds completed extractions.

The schema is created by Alembic migrations (app/migrations); keep both in sync.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime, utcnow
from app.schemas import DocumentSchema

UserStatus = Literal["pending", "active", "rejected", "suspended"]
USER_STATUSES = ("pending", "active", "rejected", "suspended", "deleted")  # deleted: anonymized
PLAN_IDS = ("free", "starter", "pro", "business", "ultra")
PAYMENT_KINDS = ("pass", "subscription", "pages")  # "pass": legacy one-time 30-day plan


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("status", USER_STATUSES), name="ck_users_status"),
        CheckConstraint(_in("plan", PLAN_IDS), name="ck_users_plan"),
        CheckConstraint("daily_limit_override IS NULL OR daily_limit_override >= 0", name="ck_users_daily_limit"),
        CheckConstraint("page_credits >= 0", name="ck_users_page_credits"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)  # always stored lowercase
    email_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # None: not verified yet
    name: Mapped[str | None] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # None for Google-only accounts
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    plan: Mapped[str] = mapped_column(String(16), default="free")
    plan_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())  # None: no expiry
    # Set by the admin: pages per plan window, beats the plan (the column keeps its original name).
    daily_limit_override: Mapped[int | None] = mapped_column(Integer)
    page_credits: Mapped[int] = mapped_column(Integer, default=0)  # prepaid pages (page packs), never expire
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_events_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[uuid.UUID] = mapped_column(index=True)
    pages: Mapped[int] = mapped_column(Integer, default=1)  # pages of the PDF (all of them count)
    credits_used: Mapped[int] = mapped_column(Integer, default=0)  # part paid with prepaid pages
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint(_in("kind", PAYMENT_KINDS), name="ck_payments_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16), default="paypal")
    kind: Mapped[str] = mapped_column(String(16), default="pass")  # one-time pass or subscription renewal
    # One-time pass: the order ID. Subscription renewal: the sale ID. Unique: recorded once.
    provider_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    # The capture (pass) or sale (subscription) ID that PayPal names in refund events.
    provider_capture_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True
    )
    plan: Mapped[str] = mapped_column(String(16))  # the subscription plan, or the pack id for page packs
    pages: Mapped[int | None] = mapped_column(Integer)  # pages bought (page packs only)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16))  # COMPLETED, REFUNDED or REVERSED
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, index=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (CheckConstraint(_in("plan", PLAN_IDS), name="ck_subscriptions_plan"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_subscription_id: Mapped[str] = mapped_column(String(64), unique=True)
    plan: Mapped[str] = mapped_column(String(16))
    # PayPal's status: APPROVAL_PENDING, APPROVED, ACTIVE, SUSPENDED, CANCELLED or EXPIRED.
    status: Mapped[str] = mapped_column(String(24), index=True)
    next_billing_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)


class PayPalPlan(Base):
    """A PayPal billing plan, created on first use for one Extracta plan at one price."""

    __tablename__ = "paypal_plans"
    __table_args__ = (UniqueConstraint("env", "plan", "price", name="uq_paypal_plans_env_plan_price"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    env: Mapped[str] = mapped_column(String(8))  # sandbox or live: they have separate catalogs
    plan: Mapped[str] = mapped_column(String(16))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    paypal_product_id: Mapped[str] = mapped_column(String(64))
    paypal_plan_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    provider_event_id: Mapped[str] = mapped_column(String(64), unique=True)
    event_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


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
