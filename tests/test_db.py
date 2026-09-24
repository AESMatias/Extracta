"""Database tests.

Unit tests run everywhere. Tests marked `integration` talk to the real Supabase
database and run only when DATABASE_URL is set, e.g.:

    docker run --rm --env-file .env -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest -m integration
"""

import os
import uuid

import pytest
from sqlalchemy import delete, select, text

from app.db import build_engine, init_db, session_scope
from app.models import Document
from app.schemas import DocumentSchema


def test_engine_uses_a_small_pool() -> None:
    # create_engine() does not connect yet, so no database is needed here.
    engine = build_engine("postgresql+psycopg://user:secret@db.example.com:5432/app")

    assert engine.pool.size() == 2  # type: ignore[attr-defined]
    assert engine.url.drivername == "postgresql+psycopg"


integration = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs a real DATABASE_URL")


@pytest.mark.integration
@integration
def test_init_db_creates_the_table_with_row_level_security() -> None:
    init_db()

    with session_scope() as session:
        rls_enabled = session.execute(
            text("select relrowsecurity from pg_class where relname = 'documents' and relkind = 'r'")
        ).scalar_one()

    assert rls_enabled is True


@pytest.mark.integration
@integration
def test_document_round_trip() -> None:
    init_db()
    task_id = uuid.uuid4()
    extraction = DocumentSchema.model_validate(
        {"document_type": "other", "summary": "Integration test row, deleted at the end."}
    )

    try:
        with session_scope() as session:
            session.add(
                Document.from_extraction(
                    task_id=task_id, filename="test.pdf", extraction=extraction, llm_provider="test", llm_model="test"
                )
            )

        with session_scope() as session:
            row = session.execute(select(Document).where(Document.id == task_id)).scalar_one()
            assert row.filename == "test.pdf"
            assert row.data["summary"] == "Integration test row, deleted at the end."
            assert row.created_at is not None
    finally:
        with session_scope() as session:
            session.execute(delete(Document).where(Document.id == task_id))
