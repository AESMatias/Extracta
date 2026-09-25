import csv
import io
import uuid
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from app.db import session_scope, utcnow
from app.models import Document, User
from app.schemas import DocumentSchema
from app.web.queue import TaskStatus
from app.web.routes import MAX_EXPORT_BODY_BYTES
from tests.conftest import Harness

MakePdf = Callable[[list[str]], Path]
INVOICE_DOC = {
    "document_type": "invoice",
    "summary": "Invoice from Acme.",
    "commercial": {"issuer": {"name": "Acme SpA"}, "currency": "CLP", "total_amount": 119000},
}


def paid() -> dict[str, Any]:
    return {"plan": "starter", "plan_expires_at": utcnow() + timedelta(days=30)}


def pdf(make_pdf: MakePdf, name: str) -> tuple[io.BytesIO, str]:
    return io.BytesIO(make_pdf([f"Invoice text for {name} with enough characters."]).read_bytes()), name


def upload(client: Any, files: list[tuple[io.BytesIO, str]], **query: str) -> Any:
    qs = "&".join(f"{k}={v}" for k, v in query.items())
    return client.post(f"/api/upload?{qs}", data={"files": files}, content_type="multipart/form-data")


# --------------------------------------------------------------------------- upload: accounts and plans


def test_upload_needs_an_account(harness: Harness, make_pdf: MakePdf) -> None:
    response = upload(harness.client(), [pdf(make_pdf, "a.pdf")])

    assert response.status_code == 401
    assert harness.queue.enqueued == []


def test_free_user_uploads_a_pdf(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up()

    response = upload(client, [pdf(make_pdf, "Factura N° 2.pdf")])

    assert response.status_code == 202
    body = response.get_json()
    assert [t["filename"] for t in body["tasks"]] == ["Factura N° 2.pdf"]
    assert body["usage"] == {"used": 1, "limit": 2}
    [job] = harness.queue.enqueued
    assert job["save_to_db"] is False
    assert job["path"].exists()  # the worker will find the file
    with session_scope() as db:
        assert job["user_id"] == str(db.query(User).one().id)


def test_free_plan_allows_two_files_per_upload(harness: Harness, make_pdf: MakePdf) -> None:
    response = upload(harness.signed_up(), [pdf(make_pdf, f"{i}.pdf") for i in range(3)])

    assert response.status_code == 400
    assert "2 files per upload" in response.get_json()["error"]
    assert response.get_json()["upgrade"] is True


def test_free_plan_allows_two_pdfs_per_24_hours(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up()
    assert upload(client, [pdf(make_pdf, "a.pdf"), pdf(make_pdf, "b.pdf")]).status_code == 202

    response = upload(client, [pdf(make_pdf, "c.pdf")])

    assert response.status_code == 429
    body = response.get_json()
    assert "limit of 2 PDFs in 24 hours" in body["error"]
    assert body["next_slot_at"] is not None
    assert len(harness.queue.enqueued) == 2


def test_files_beyond_the_remaining_quota_are_rejected(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up(**paid(), daily_limit_override=1)

    body = upload(client, [pdf(make_pdf, "a.pdf"), pdf(make_pdf, "b.pdf")]).get_json()

    assert [t["filename"] for t in body["tasks"]] == ["a.pdf"]
    assert body["rejected"] == [{"filename": "b.pdf", "error": "Daily limit reached"}]


def test_saving_to_the_database_is_a_paid_privilege(harness: Harness, make_pdf: MakePdf) -> None:
    free = upload(harness.signed_up(), [pdf(make_pdf, "a.pdf")], save_to_db="true")
    paid_user = upload(harness.signed_up("bob@example.com", **paid()), [pdf(make_pdf, "a.pdf")], save_to_db="true")

    assert free.status_code == 403
    assert free.get_json()["upgrade"] is True
    assert paid_user.status_code == 202
    assert harness.queue.enqueued[-1]["save_to_db"] is True


def test_expired_pass_goes_back_to_free_limits(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up(plan="pro", plan_expires_at=utcnow() - timedelta(minutes=1))

    response = upload(client, [pdf(make_pdf, "a.pdf")], save_to_db="true")

    assert response.status_code == 403


def test_pending_accounts_cannot_upload(harness: Harness, make_pdf: MakePdf) -> None:
    response = upload(harness.signed_up(status="pending"), [pdf(make_pdf, "a.pdf")])

    assert response.status_code == 403
    assert "waiting for approval" in response.get_json()["error"]


def test_one_upload_at_a_time_per_account(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up()
    with session_scope() as db:
        user_id = db.query(User).one().id
    harness.redis.set(f"upload-lock:{user_id}", "1")  # another upload is running

    response = upload(client, [pdf(make_pdf, "a.pdf")])

    assert response.status_code == 409


def test_bad_files_are_rejected_without_blocking_the_others(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up(**paid())  # Starter: 20 MB per file
    too_big = (io.BytesIO(b"%PDF-1.4\n" + b"0" * (21 * 1024 * 1024)), "huge.pdf")

    body = upload(client, [pdf(make_pdf, "ok.pdf"), (io.BytesIO(b"\x89PNG"), "photo.pdf"), too_big]).get_json()

    assert [t["filename"] for t in body["tasks"]] == ["ok.pdf"]
    assert {r["filename"]: r["error"] for r in body["rejected"]} == {
        "photo.pdf": "file is not a PDF",
        "huge.pdf": "file is larger than 20 MB",
    }
    assert body["usage"]["used"] == 1  # rejected files do not count against the quota


def test_upload_without_files_is_a_400(harness: Harness) -> None:
    response = harness.signed_up().post("/api/upload", data={}, content_type="multipart/form-data")

    assert response.status_code == 400


# --------------------------------------------------------------------------- task status and ownership


def uploaded_task(client: Any, make_pdf: MakePdf) -> str:
    task_id: str = upload(client, [pdf(make_pdf, "a.pdf")]).get_json()["tasks"][0]["task_id"]
    return task_id


def test_owner_reads_its_task(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up()
    task_id = uploaded_task(client, make_pdf)
    harness.queue.statuses[task_id] = TaskStatus(status="completed", result={"document": INVOICE_DOC})

    response = client.get(f"/api/tasks/{task_id}")

    assert response.get_json() == {"task_id": task_id, "status": "completed", "result": {"document": INVOICE_DOC}}


def test_other_accounts_cannot_read_a_task(harness: Harness, make_pdf: MakePdf) -> None:
    task_id = uploaded_task(harness.signed_up(), make_pdf)
    stranger = harness.signed_up("eve@example.com")

    assert stranger.get(f"/api/tasks/{task_id}").status_code == 404
    assert harness.client().get(f"/api/tasks/{task_id}").status_code == 401
    assert stranger.get("/api/tasks/not-a-uuid").status_code == 404


def test_batch_status_only_reveals_own_tasks(harness: Harness, make_pdf: MakePdf) -> None:
    client = harness.signed_up()
    mine = uploaded_task(client, make_pdf)
    foreign = uploaded_task(harness.signed_up("eve@example.com"), make_pdf)
    harness.queue.statuses[mine] = TaskStatus(status="failed", error="This PDF looks scanned.")

    tasks = client.post("/api/tasks/status", json={"task_ids": [mine, foreign, "junk"]}).get_json()["tasks"]

    assert tasks == [
        {"task_id": mine, "status": "failed", "error": "This PDF looks scanned."},
        {"task_id": foreign, "status": "not_found"},
        {"task_id": "junk", "status": "not_found"},
    ]


@pytest.mark.parametrize("payload", [{}, {"task_ids": []}, {"task_ids": ["x"] * 101}, {"task_ids": "x"}])
def test_batch_status_validates_its_input(harness: Harness, payload: dict[str, Any]) -> None:
    assert harness.signed_up().post("/api/tasks/status", json=payload).status_code == 400


# --------------------------------------------------------------------------- saved documents


def save_document(email: str) -> uuid.UUID:
    doc_id = uuid.uuid4()
    with session_scope() as db:
        user = db.query(User).filter_by(email=email).one()
        extraction = DocumentSchema.model_validate(INVOICE_DOC)
        db.add(
            Document.from_extraction(
                task_id=doc_id,
                filename="f.pdf",
                extraction=extraction,
                llm_provider="x",
                llm_model="y",
                user_id=user.id,
            )
        )
    return doc_id


def test_users_list_and_delete_only_their_saved_documents(harness: Harness) -> None:
    ana, eve = harness.signed_up(), harness.signed_up("eve@example.com")
    doc_id = save_document("ana@example.com")

    [listed] = ana.get("/api/documents").get_json()["documents"]
    assert listed["id"] == str(doc_id)
    assert listed["document"]["commercial"]["total_amount"] == 119000
    assert eve.get("/api/documents").get_json()["documents"] == []
    assert eve.delete(f"/api/documents/{doc_id}").status_code == 404
    assert ana.delete(f"/api/documents/{doc_id}").status_code == 200
    assert ana.get("/api/documents").get_json()["documents"] == []


# --------------------------------------------------------------------------- export


def rows_of(response: Any) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(response.get_data(as_text=True).removeprefix("﻿"))))


def test_export_needs_an_account(harness: Harness) -> None:
    response = harness.client().post("/api/export/csv/individual", json={"filename": "a.pdf", "document": INVOICE_DOC})

    assert response.status_code == 401


def test_individual_csv_download(harness: Harness) -> None:
    response = harness.signed_up().post(
        "/api/export/csv/individual", json={"filename": "Factura N° 2.pdf", "document": INVOICE_DOC}
    )

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    disposition = response.headers["Content-Disposition"]
    assert 'filename="Factura_N_2.csv"' in disposition
    assert "filename*=UTF-8''Factura%20N%C2%B0%202.csv" in disposition
    assert rows_of(response)[0]["issuer.name"] == "Acme SpA"


@pytest.mark.parametrize(
    ("fmt", "mimetype"),
    [
        ("csv", "text/csv"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("json", "application/json"),
    ],
)
def test_every_format_downloads(harness: Harness, fmt: str, mimetype: str) -> None:
    client = harness.signed_up()
    for url, payload in [
        (f"/api/export/{fmt}/individual", {"filename": "a.pdf", "document": INVOICE_DOC}),
        (f"/api/export/{fmt}/unified", {"items": [{"filename": "a.pdf", "document": INVOICE_DOC}]}),
    ]:
        response = client.post(url, json=payload)
        assert response.get_data()
        assert response.status_code == 200
        assert response.mimetype == mimetype
        assert f'.{fmt}"' in response.headers["Content-Disposition"]


def test_export_rejects_bad_input(harness: Harness) -> None:
    client = harness.signed_up()
    bad = {"filename": "a.pdf", "document": {"document_type": "invoice", "summary": "SECRET no section"}}

    invalid = client.post("/api/export/csv/individual", json=bad)
    unknown = client.post("/api/export/pdf/individual", json={"filename": "a.pdf", "document": INVOICE_DOC})
    not_json = client.post("/api/export/csv/unified", data="x", content_type="text/plain")
    huge = client.post(
        "/api/export/csv/unified",
        data=b'{"items": [' + b" " * (MAX_EXPORT_BODY_BYTES + 1) + b"]}",
        content_type="application/json",
    )

    assert invalid.status_code == 400
    assert "SECRET" not in invalid.get_data(as_text=True)  # never echo submitted content
    assert unknown.status_code == 404
    assert not_json.status_code == 400
    assert huge.status_code == 413


# --------------------------------------------------------------------------- cross-cutting


def test_cross_site_requests_are_refused(harness: Harness) -> None:
    client = harness.signed_up()
    body = {"filename": "a.pdf", "document": INVOICE_DOC}

    evil = client.post("/api/export/json/individual", json=body, headers={"Origin": "https://evil.example"})
    ours = client.post("/api/export/json/individual", json=body, headers={"Origin": "http://localhost:8080"})

    assert evil.status_code == 403
    assert ours.status_code == 200


def test_api_responses_are_hardened(harness: Harness) -> None:
    response = harness.client().get("/api/health")

    assert response.get_json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_unknown_api_routes_answer_json(harness: Harness) -> None:
    response = harness.client().get("/api/nope")

    assert response.status_code == 404
    assert "error" in response.get_json()
