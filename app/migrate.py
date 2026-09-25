"""Apply database migrations (Alembic):  python -m app.migrate

The web container runs this before starting gunicorn, so a deploy always has the current schema.
A database created before Alembic existed (only the step-6 `documents` table) is adopted as
revision 0001 instead of being recreated.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.db import get_engine

BASELINE = "0001"


def alembic_config(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
    config.attributes["connection"] = connection
    return config


def upgrade() -> None:
    with get_engine().begin() as connection:
        tables = set(inspect(connection).get_table_names())
        config = alembic_config(connection)
        if "documents" in tables and "alembic_version" not in tables:
            command.stamp(config, BASELINE)  # table created before Alembic: adopt it
        command.upgrade(config, "head")
        # Alembic's own bookkeeping table must not be exposed through Supabase's REST API either.
        connection.execute(text("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY"))


if __name__ == "__main__":  # pragma: no cover
    upgrade()
    print("Database schema is up to date (Row Level Security enabled on every table).")
