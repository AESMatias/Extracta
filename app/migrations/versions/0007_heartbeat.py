"""A single row rewritten periodically, so the database always shows recent activity.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "heartbeat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("beat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("beats", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.execute("ALTER TABLE heartbeat ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("heartbeat")
