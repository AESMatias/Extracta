"""Create the documents table (baseline: it existed before Alembic, created in step 6).

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8)),
        sa.Column("title", sa.Text()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("llm_provider", sa.String(32), nullable=False),
        sa.Column("llm_model", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    # RLS with no policies: Supabase's public REST API cannot read the table; the app owns it.
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("documents")
