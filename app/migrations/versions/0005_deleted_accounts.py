"""Allow the "deleted" status for accounts erased by their owner (kept anonymized for payments).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.create_check_constraint(
        "ck_users_status", "users", "status IN ('pending', 'active', 'rejected', 'suspended', 'deleted')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.create_check_constraint("ck_users_status", "users", "status IN ('pending', 'active', 'rejected', 'suspended')")
