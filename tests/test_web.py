import csv
import io
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from pydantic import SecretStr

from app import create_app
from app.config import Settings
from app.web.queue import TaskStatus
from app.web.routes import MAX_FILES_PER_UPLOAD

MakePdf = Callable[[list[str]], Path]
INVOICE_DOC = {
    "document_type": "invoice",
    "summary": "Invoice from Acme.",
    "commercial": {"issuer": {"name": "Acme SpA"}, "currency": "CLP", "total_amount": 119000},
}


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[Path, str, bool]] = []
        self.statuses: dict[str, TaskStatus] = {}

    def enqueue(self, file_path: Path, filename: str, save_to_db: bool) -> str:
        self.enqueued.append((file_path, filename, save_to_db))
        task_id = str(uuid.uuid4())
        self.statuses[task_id] = TaskStatus(status="pending")
        return task_id

    def status(self, task_id: str) -> TaskStatus:
        return self.statuses.get(task_id, TaskStatus(status="pending"))


class MemoryOwnership:
    def __init__(self) -> None:
        self.owned: dict[str, set[str]] = {}

    def add(self, owner: str, task_ids: list[str]) -> None:
        self.owned.setdefault(owner, set()).update(task_ids)

    def owns(self, owner: str, task_id: str) -> bool:
        return task_id in self.owned.get(owner, set())


@pytest.fixture
def queue() -> FakeQueue:
    return FakeQueue()


@pytest.fixture
def app(tmp_path: Path, queue: FakeQueue) -> Flask:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        gemini_api_key=SecretStr("test"),
        database_url=SecretStr("postgresql+psycopg://u:p@h:5432/d"),
        secret_key=SecretStr("k" * 32),
        upload_dir=tmp_path / "uploads",
        max_upload_mb=1,
    )
    return create_app(settings, task_queue=queue, ownership=MemoryOwnership())


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def pdf_file(make_pdf: MakePdf, name: str) -> tuple[io.BytesIO, str]:
    return io.BytesIO(make_pdf([f"Invoice text for {name} with enough characters."]).read_bytes()), name


def upload(client: FlaskClient, files: list[tuple[io.BytesIO, str]], **form: str) -> Any:
    return client.post("/upload", data={"files": files, **form}, content_type="multipart/form-data")


# --------------------------------------------------------------------------- upload


def test_upload_enqueues_one_task_per_pdf(client: FlaskClient, queue: FakeQueue, make_pdf: MakePdf) -> None:
    response = upload(client, [pdf_file(make_pdf, "a.pdf"), pdf_file(make_pdf, "Factura N° 2.pdf")], save_to_db="true")

    assert response.status_code == 202
    body = response.get_json()
    assert body["save_to_db"] is True
    assert [t["filename"] for t in body["tasks"]] == ["a.pdf", "Factura N° 2.pdf"]
    assert body["rejected"] == []
    assert [(name, save) for _, name, save in queue.enqueued] == [("a.pdf", True), ("Factura N° 2.pdf", True)]
    assert all(path.exists() for path, _, _ in queue.enqueued)  # the worker will find the files


def test_ephemeral_is_the_default_mode(client: FlaskClient, queue: FakeQueue, make_pdf: MakePdf) -> None:
    response = upload(client, [pdf_file(make_pdf, "a.pdf")])

    assert response.get_json()["save_to_db"] is False
    assert queue.enqueued[0][2] is False


def test_bad_files_are_rejected_without_blocking_the_others(
    client: FlaskClient, queue: FakeQueue, make_pdf: MakePdf
) -> None:
    fake_pdf = (io.BytesIO(b"\x89PNG not a pdf"), "photo.pdf")
    too_big = (io.BytesIO(b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)), "huge.pdf")

    response = upload(client, [pdf_file(make_pdf, "ok.pdf"), fake_pdf, too_big])

    body = response.get_json()
    assert response.status_code == 202
    assert [t["filename"] for t in body["tasks"]] == ["ok.pdf"]
    assert {r["filename"]: r["error"] for r in body["rejected"]} == {
        "photo.pdf": "file is not a PDF",
        "huge.pdf": "file is larger than 1 MB",
    }
    assert len(queue.enqueued) == 1


def test_upload_with_only_bad_files_is_a_400(client: FlaskClient) -> None:
    response = upload(client, [(io.BytesIO(b"hello"), "notes.pdf")])

    assert response.status_code == 400
    assert response.get_json()["tasks"] == []


def test_upload_without_files_is_a_400(client: FlaskClient) -> None:
    response = client.post("/upload", data={}, content_type="multipart/form-data")

    assert response.status_code == 400
    assert "files" in response.get_json()["error"]


def test_too_many_files_is_a_400(client: FlaskClient, make_pdf: MakePdf) -> None:
    files = [pdf_file(make_pdf, f"{i}.pdf") for i in range(MAX_FILES_PER_UPLOAD + 1)]

    response = upload(client, files)

    assert response.status_code == 400


# --------------------------------------------------------------------------- task status + ownership


def test_owner_can_read_the_status_of_its_tasks(client: FlaskClient, queue: FakeQueue, make_pdf: MakePdf) -> None:
    task_id = upload(client, [pdf_file(make_pdf, "a.pdf")]).get_json()["tasks"][0]["task_id"]
    queue.statuses[task_id] = TaskStatus(status="completed", result={"document": INVOICE_DOC})

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.get_json() == {"task_id": task_id, "status": "completed", "result": {"document": INVOICE_DOC}}


def test_failed_task_returns_a_readable_error(client: FlaskClient, queue: FakeQueue, make_pdf: MakePdf) -> None:
    task_id = upload(client, [pdf_file(make_pdf, "a.pdf")]).get_json()["tasks"][0]["task_id"]
    queue.statuses[task_id] = TaskStatus(status="failed", error="This PDF looks scanned.")

    body = client.get(f"/tasks/{task_id}").get_json()

    assert body["status"] == "failed"
    assert body["error"] == "This PDF looks scanned."


def test_another_browser_cannot_read_someone_elses_task(app: Flask, make_pdf: MakePdf) -> None:
    owner, stranger = app.test_client(), app.test_client()
    task_id = upload(owner, [pdf_file(make_pdf, "a.pdf")]).get_json()["tasks"][0]["task_id"]

    assert owner.get(f"/tasks/{task_id}").status_code == 200
    assert stranger.get(f"/tasks/{task_id}").status_code == 404  # 404, not 403: do not confirm it exists


def test_unknown_or_malformed_task_ids_are_404(client: FlaskClient) -> None:
    assert client.get(f"/tasks/{uuid.uuid4()}").status_code == 404
    assert client.get("/tasks/not-a-uuid").status_code == 404


def test_session_cookie_is_protected(client: FlaskClient, make_pdf: MakePdf) -> None:
    response = upload(client, [pdf_file(make_pdf, "a.pdf")])

    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie  # not readable from JavaScript
    assert "SameSite=Lax" in cookie  # not sent on cross-site POSTs (CSRF)


# --------------------------------------------------------------------------- CSV export


def rows_of(response: Any) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(response.get_data(as_text=True).removeprefix("﻿"))))


def test_individual_csv_download(client: FlaskClient) -> None:
    response = client.post("/export/csv/individual", json={"filename": "Factura N° 2.pdf", "document": INVOICE_DOC})

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    disposition = response.headers["Content-Disposition"]
    assert 'filename="Factura_N_2.csv"' in disposition  # ASCII fallback
    assert "filename*=UTF-8''Factura%20N%C2%B0%202.csv" in disposition  # exact name for modern browsers
    [row] = rows_of(response)
    assert row["issuer.name"] == "Acme SpA"


def test_unified_csv_download(client: FlaskClient) -> None:
    items = [{"filename": "a.pdf", "document": INVOICE_DOC}, {"filename": "b.pdf", "document": INVOICE_DOC}]

    response = client.post("/export/csv/unified", json={"items": items})

    assert response.status_code == 200
    assert "documents-" in response.headers["Content-Disposition"]
    assert [r["filename"] for r in rows_of(response)] == ["a.pdf", "b.pdf"]


def test_export_rejects_data_that_breaks_the_schema(client: FlaskClient) -> None:
    bad = {"filename": "a.pdf", "document": {"document_type": "invoice", "summary": "SECRET no section"}}

    response = client.post("/export/csv/individual", json=bad)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Invalid document data."
    assert "SECRET" not in response.get_data(as_text=True)  # never echo the submitted content


def test_export_needs_a_json_body(client: FlaskClient) -> None:
    response = client.post("/export/csv/unified", data="not json", content_type="text/plain")

    assert response.status_code == 400


def test_export_does_not_need_a_session(app: Flask) -> None:
    # Exports only transform the JSON the browser sends; they never read server data.
    fresh = app.test_client()

    response = fresh.post("/export/csv/individual", json={"filename": "a.pdf", "document": INVOICE_DOC})

    assert response.status_code == 200
