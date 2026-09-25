"""Shared pytest fixtures."""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  # registers every table on Base.metadata
from app.db import Base, use_engine


def build_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one text page per item ("" makes a page with no text layer).

    Uses the built-in Helvetica font with WinAnsi encoding, so Latin-1 text such as
    "Factura electrónica" round-trips. Lines are split on "\\n".
    """
    page_count = len(pages)
    # Object numbers: 1 catalog, 2 page tree, 3 font, then (page, content) pairs.
    page_ids = [4 + 2 * i for i in range(page_count)]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % i for i in page_ids) + b"] /Count %d >>" % page_count,
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    for page_id, text in zip(page_ids, pages, strict=True):
        content = b""
        if text:
            lines = [
                line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")
                for line in text.split("\n")
            ]
            content = b"BT /F1 12 Tf 72 720 Td 14 TL " + b" ".join(b"(" + line + b") '" for line in lines) + b" ET"
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (page_id + 1)
        )
        objects[page_id + 1] = b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_at)
    return bytes(out)


@pytest.fixture
def make_pdf(tmp_path: Path) -> Callable[[list[str]], Path]:
    """Return a function that writes a PDF with the given page texts and returns its path."""
    counter = 0

    def _make(pages: list[str]) -> Path:
        nonlocal counter
        counter += 1
        path = tmp_path / f"generated-{counter}.pdf"
        path.write_bytes(build_pdf(pages))
        return path

    return _make


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    """An in-memory SQLite database with the app's tables, used by session_scope() during the test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # SQLite ignores FKs unless asked

    Base.metadata.create_all(engine)
    use_engine(engine)
    yield engine
    use_engine(None)
    engine.dispose()


ADMIN_PASSWORD = "admin-password-123"
USER_PASSWORD = "correct horse battery"


class Harness:
    """A test app wired to fakes, plus helpers to act as a browser."""

    def __init__(self, tmp_path: Path, **overrides: Any) -> None:
        from pydantic import SecretStr

        from app import create_app
        from app.config import Settings
        from tests.fakes import FakeGoogle, FakePayPal, FakeQueue, FakeRedis

        values: dict[str, Any] = {
            "gemini_api_key": SecretStr("test"),
            "database_url": SecretStr("postgresql+psycopg://u:p@h:5432/d"),
            "secret_key": SecretStr("k" * 32),
            "upload_dir": tmp_path / "uploads",
            "admin_password": SecretStr(ADMIN_PASSWORD),
            "public_base_url": "http://localhost:8080",
            **overrides,
        }
        self.settings = Settings(_env_file=None, **values)  # type: ignore[call-arg]
        self.queue = FakeQueue()
        self.redis = FakeRedis()
        self.paypal = FakePayPal()
        self.google = FakeGoogle()
        self.app = create_app(
            self.settings,
            task_queue=self.queue,
            redis_client=self.redis,
            google=self.google,  # type: ignore[arg-type]
            paypal=self.paypal,  # type: ignore[arg-type]
        )

    def client(self) -> Any:
        return self.app.test_client()

    def signed_up(self, email: str = "ana@example.com", **user_changes: Any) -> Any:
        """A browser signed in to a new account; optional changes to the account (plan, status...)."""
        from sqlalchemy import select

        from app.db import session_scope
        from app.models import User

        client = self.client()
        response = client.post("/api/auth/register", json={"email": email, "password": USER_PASSWORD, "name": "Ana"})
        assert response.status_code == 201, response.get_json()
        if user_changes:
            with session_scope() as db:
                user = db.execute(select(User).where(User.email == email)).scalar_one()
                for key, value in user_changes.items():
                    setattr(user, key, value)
        return client

    def admin(self) -> Any:
        client = self.client()
        assert client.post("/api/admin/login", json={"password": ADMIN_PASSWORD}).status_code == 200
        return client


@pytest.fixture
def harness(db_engine: Engine, tmp_path: Path) -> Harness:
    return Harness(tmp_path)
