"""Database access: SQLAlchemy 2 engine and sessions for Supabase PostgreSQL.

Used only in persistent mode (`save_to_db=True`); ephemeral processing never
imports a session. Create the tables once with:

    docker compose run --rm web python -m app.db
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Parent class of every table model (see app/models.py)."""


def build_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=2,  # small pool: 2 GB server and a single Celery worker
        max_overflow=2,
        pool_pre_ping=True,  # replace connections the Supabase pooler closed while idle
        pool_recycle=300,
        connect_args={"sslmode": "require", "connect_timeout": 10},
    )


@lru_cache
def get_engine() -> Engine:
    # Built lazily on first use, so each gunicorn/Celery process gets its own connections.
    return build_engine(get_settings().database_url.get_secret_value())


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Open a session that commits on success and rolls back on any error."""
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create missing tables and turn on Row Level Security (safe to run many times)."""
    import app.models  # noqa: F401  # registers the models on Base.metadata

    engine = get_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            # RLS with no policies blocks Supabase's public REST API from reading the table.
            # This app connects as the table owner, which RLS does not restrict.
            connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))


if __name__ == "__main__":  # pragma: no cover
    init_db()
    print("Database ready: tables created and Row Level Security enabled.")
