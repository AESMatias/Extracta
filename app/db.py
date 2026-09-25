"""Database access: SQLAlchemy 2 engine and sessions for Supabase PostgreSQL.

The schema is managed by Alembic migrations (app/migrations, run with `python -m app.migrate`).
Tests plug in an in-memory SQLite engine with `use_engine()`, so column types here stay portable:
UTCDateTime keeps timestamps timezone-aware on every backend.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect, Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


class Base(DeclarativeBase):
    """Parent class of every table model (see app/models.py)."""


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """A timestamp that is always stored in UTC and always read back timezone-aware."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime: use timezone-aware UTC datetimes")
        return value.astimezone(UTC)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)  # SQLite drops the tz


def build_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=2,  # small pool: 2 GB server, few concurrent requests
        max_overflow=3,
        pool_pre_ping=True,  # replace connections the Supabase pooler closed while idle
        pool_recycle=300,
        connect_args={"sslmode": "require", "connect_timeout": 10},
    )


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    # Built lazily on first use, so each gunicorn/Celery process gets its own connections.
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings().database_url.get_secret_value())
    return _engine


def use_engine(engine: Engine | None) -> None:
    """Replace the engine (tests use an in-memory SQLite database). None resets to the default."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = None


def _sessions() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a session that commits on success and rolls back on any error."""
    session = _sessions()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
