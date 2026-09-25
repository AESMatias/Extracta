"""Database tests.

Unit tests run everywhere. Tests marked `integration` run the real migrations against Supabase and
need DATABASE_URL, e.g.:

    docker run --rm --env-file .env -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest -m integration
"""

import os
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, delete, select, text

from app.db import build_engine, session_scope, use_engine
from app.models import Document, User
from app.schemas import DocumentSchema


def test_engine_uses_a_small_pool() -> None:
    # create_engine() does not connect yet, so no database is needed here.
    engine = build_engine("postgresql+psycopg://user:secret@db.example.com:5432/app")

    assert engine.pool.size() == 2  # type: ignore[attr-defined]
    assert engine.url.drivername == "postgresql+psycopg"


def test_timestamps_are_stored_in_utc_and_read_back_aware(db_engine: Engine) -> None:
    santiago = timezone(timedelta(hours=-3))
    with session_scope() as db:
        user = User(email="ana@example.com", plan_expires_at=datetime(2026, 9, 24, 9, 0, tzinfo=santiago))
        db.add(user)

    with session_scope() as db:
        stored = db.execute(select(User)).scalar_one()

    assert stored.plan_expires_at == datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
    assert stored.created_at.tzinfo is not None


def test_naive_datetimes_are_refused(db_engine: Engine) -> None:
    with pytest.raises(Exception, match="naive"), session_scope() as db:
        db.add(User(email="ana@example.com", plan_expires_at=datetime(2026, 9, 24, 12, 0)))


integration = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs a real DATABASE_URL")


@pytest.fixture
def supabase() -> Engine:
    use_engine(None)  # the real engine from DATABASE_URL
    from app.db import get_engine

    return get_engine()


@pytest.mark.integration
@integration
def test_migrations_create_every_table_with_row_level_security(supabase: Engine) -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.db import Base
    from app.migrate import upgrade

    upgrade()
    upgrade()  # idempotent: a second run changes nothing

    tables = (*Base.metadata.tables, "alembic_version")  # every table the models declare
    with session_scope() as db:
        rls = dict(
            db.execute(
                text("select relname, relrowsecurity from pg_class where relname = any(:names) and relkind = 'r'"),
                {"names": list(tables)},
            )
            .tuples()
            .all()
        )
        version = db.execute(text("select version_num from alembic_version")).scalar_one()

    assert rls == dict.fromkeys(tables, True)
    config = Config()
    config.set_main_option("script_location", "app/migrations")
    assert version == ScriptDirectory.from_config(config).get_current_head()


@pytest.mark.integration
@integration
def test_document_round_trip_with_its_owner(supabase: Engine) -> None:
    from app.migrate import upgrade

    upgrade()
    task_id = uuid.uuid4()
    email = f"it-{uuid.uuid4().hex[:8]}@example.com"
    extraction = DocumentSchema.model_validate({"document_type": "other", "summary": "Integration test row."})

    try:
        with session_scope() as db:
            owner = User(email=email)
            db.add(owner)
            db.flush()
            db.add(
                Document.from_extraction(
                    task_id=task_id,
                    filename="test.pdf",
                    extraction=extraction,
                    llm_provider="test",
                    llm_model="test",
                    user_id=owner.id,
                )
            )

        with session_scope() as db:
            row = db.execute(select(Document).where(Document.id == task_id)).scalar_one()
            assert row.data["summary"] == "Integration test row."
            assert row.user_id is not None
            assert row.created_at.tzinfo is not None
    finally:
        with session_scope() as db:
            db.execute(delete(User).where(User.email == email))  # cascades to the document

    with session_scope() as db:
        assert db.get(Document, task_id) is None
