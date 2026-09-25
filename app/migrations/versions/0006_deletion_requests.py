"""Record account deletion requests from the public form, for the admin panel.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending', 'completed', 'dismissed')", name="ck_deletion_requests_status"),
    )
    op.create_index("ix_deletion_requests_user_id", "deletion_requests", ["user_id"])
    op.create_index("ix_deletion_requests_status", "deletion_requests", ["status"])
    op.execute("ALTER TABLE deletion_requests ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("deletion_requests")
