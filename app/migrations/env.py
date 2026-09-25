"""Alembic environment. Run migrations with:  python -m app.migrate"""

from alembic import context
from sqlalchemy.engine import Connection

import app.models  # noqa: F401  # registers every table on Base.metadata
from app.db import Base, get_engine

target_metadata = Base.metadata


def run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline (SQL script) migrations are not supported; run python -m app.migrate")

# app.migrate passes an open connection; the alembic CLI gets one from the app's engine.
shared = context.config.attributes.get("connection")
if shared is not None:
    run(shared)
else:
    with get_engine().connect() as connection:
        run(connection)
