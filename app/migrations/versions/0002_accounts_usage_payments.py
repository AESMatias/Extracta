"""Add accounts, usage quota events, payments and document ownership.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = "'pending', 'active', 'rejected', 'suspended'"
PLANS = "'free', 'starter', 'pro', 'business', 'ultra'"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(120)),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("google_sub", sa.String(255), unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(16), nullable=False, server_default="free"),
        sa.Column("plan_expires_at", sa.DateTime(timezone=True)),
        sa.Column("daily_limit_override", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(f"status IN ({STATUSES})", name="ck_users_status"),
        sa.CheckConstraint(f"plan IN ({PLANS})", name="ck_users_plan"),
        sa.CheckConstraint("daily_limit_override IS NULL OR daily_limit_override >= 0", name="ck_users_daily_limit"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_events_user_created", "usage_events", ["user_id", "created_at"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False, server_default="paypal"),
        sa.Column("provider_order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_created_at", "payments", ["created_at"])

    op.add_column("documents", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_documents_user_id", "documents", "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    for table in ("users", "usage_events", "payments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_documents_user_id", "documents")
    op.drop_constraint("fk_documents_user_id", "documents", type_="foreignkey")
    op.drop_column("documents", "user_id")
    op.drop_table("payments")
    op.drop_table("usage_events")
    op.drop_table("users")
