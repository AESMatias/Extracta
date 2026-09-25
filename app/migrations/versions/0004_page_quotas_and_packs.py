"""Measure usage in pages and add prepaid page packs.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("page_credits", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_users_page_credits", "users", "page_credits >= 0")

    # Earlier uploads were one document each: count them as one page.
    op.add_column("usage_events", sa.Column("pages", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("usage_events", sa.Column("credits_used", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_usage_events_task_id", "usage_events", ["task_id"])

    op.add_column("payments", sa.Column("pages", sa.Integer()))
    op.drop_constraint("ck_payments_kind", "payments", type_="check")
    op.create_check_constraint("ck_payments_kind", "payments", "kind IN ('pass', 'subscription', 'pages')")


def downgrade() -> None:
    op.drop_constraint("ck_payments_kind", "payments", type_="check")
    op.create_check_constraint("ck_payments_kind", "payments", "kind IN ('pass', 'subscription')")
    op.drop_column("payments", "pages")
    op.drop_index("ix_usage_events_task_id", "usage_events")
    op.drop_column("usage_events", "credits_used")
    op.drop_column("usage_events", "pages")
    op.drop_constraint("ck_users_page_credits", "users", type_="check")
    op.drop_column("users", "page_credits")
