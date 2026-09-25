"""Add email verification, PayPal subscriptions, PayPal billing plans and processed webhook events.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLANS = "'free', 'starter', 'pro', 'business', 'ultra'"


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    # Accounts linked to Google already had their address verified by Google.
    op.execute("UPDATE users SET email_verified_at = created_at WHERE google_sub IS NOT NULL")

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_subscription_id", sa.String(64), nullable=False, unique=True),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("next_billing_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"plan IN ({PLANS})", name="ck_subscriptions_plan"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])

    op.create_table(
        "paypal_plans",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("env", sa.String(8), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("paypal_product_id", sa.String(64), nullable=False),
        sa.Column("paypal_plan_id", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("env", "plan", "price", name="uq_paypal_plans_env_plan_price"),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("provider_event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64)),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column("payments", sa.Column("kind", sa.String(16), nullable=False, server_default="pass"))
    op.add_column("payments", sa.Column("provider_capture_id", sa.String(64), unique=True))
    op.add_column("payments", sa.Column("subscription_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_payments_subscription_id", "payments", "subscriptions", ["subscription_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])
    op.create_check_constraint("ck_payments_kind", "payments", "kind IN ('pass', 'subscription')")

    for table in ("subscriptions", "paypal_plans", "webhook_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_constraint("ck_payments_kind", "payments", type_="check")
    op.drop_index("ix_payments_subscription_id", "payments")
    op.drop_constraint("fk_payments_subscription_id", "payments", type_="foreignkey")
    op.drop_column("payments", "subscription_id")
    op.drop_column("payments", "provider_capture_id")
    op.drop_column("payments", "kind")
    op.drop_table("webhook_events")
    op.drop_table("paypal_plans")
    op.drop_table("subscriptions")
    op.drop_column("users", "email_verified_at")
