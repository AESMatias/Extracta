import io
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from app import celery_app as celery_module
from app import tasks
from app.config import Settings
from app.llm import LLMExtractionError, LLMTransientError
from app.schemas import DocumentSchema
from app.storage import save_stream

INVOICE_TEXT = "Factura N° 1234 de Acme SpA por un total de $119.000 pesos chilenos."
VALID_DOC = DocumentSchema.model_validate(
    {
        "document_type": "invoice",
        "summary": "Invoice from Acme SpA.",
        "commercial": {"issuer": {"name": "Acme SpA"}, "currency": "CLP", "total_amount": 119000},
    }
)


class FakeExtractor:
    provider = "fake"
    model = "fake-model"

    def __init__(self, *outcomes: DocumentSchema | Exception) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0
        self.texts: list[str] = []
        self.files: list[tuple[bytes, str]] = []  # (data, mime type) sent for the model's vision

    def extract(self, text: str) -> DocumentSchema:
        self.texts.append(text)
        return self._next()

    def extract_file(self, data: bytes, mime_type: str) -> DocumentSchema:
        self.files.append((data, mime_type))
        return self._next()

    def _next(self) -> DocumentSchema:
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeSession:
    def __init__(self) -> None:
        self.merged: list[Any] = []

    def merge(self, row: Any) -> Any:
        self.merged.append(row)
        return row


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        gemini_api_key=SecretStr("test"),
        database_url=SecretStr("postgresql+psycopg://u:p@h:5432/d"),
        secret_key=SecretStr("k" * 32),
        upload_dir=tmp_path / "uploads",
    )


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> Callable[..., FakeSession]:
    """Point the task module at test settings, a fake LLM and a fake database session."""
    session = FakeSession()

    @contextmanager
    def fake_session_scope() -> Iterator[FakeSession]:
        yield session

    monkeypatch.setattr(tasks, "get_settings", lambda: settings)
    monkeypatch.setattr(celery_module, "get_settings", lambda: settings)  # Celery's lazy config
    monkeypatch.setattr(tasks, "session_scope", fake_session_scope)
    monkeypatch.setattr(tasks.process_document, "retry_backoff_seconds", lambda retries: 0)

    def install(extractor: FakeExtractor) -> FakeSession:
        monkeypatch.setattr(tasks, "get_extractor", lambda: extractor)
        return session

    return install


MakePdf = Callable[[list[str]], Path]


def upload(settings: Settings, make_pdf: MakePdf, pages: list[str] | None = None) -> Path:
    """Store a generated PDF exactly as the web app will: through save_stream()."""
    data = make_pdf(pages if pages is not None else [INVOICE_TEXT]).read_bytes()
    return save_stream(io.BytesIO(data), "factura.pdf", upload_dir=settings.upload_dir, max_bytes=10**7).path


def run(path: Path, save_to_db: bool, user_id: str | None = None) -> Any:
    # apply() runs the task in-process (no broker, no worker), including its retries.
    return tasks.process_document.apply(args=[str(path), "factura.pdf", save_to_db, user_id], task_id=str(uuid.uuid4()))


def test_ephemeral_mode_returns_data_without_touching_the_database(
    env: Any, settings: Settings, make_pdf: MakePdf
) -> None:
    session = env(FakeExtractor(VALID_DOC))
    path = upload(settings, make_pdf)

    result = run(path, save_to_db=False)

    assert result.successful()
    payload = result.get()
    assert payload["filename"] == "factura.pdf"
    assert payload["saved_to_db"] is False
    assert payload["document"]["commercial"]["total_amount"] == 119000
    assert session.merged == []  # no database write in ephemeral mode
    assert not path.exists()  # PDF deleted


def test_persistent_mode_saves_the_row_and_returns_the_data(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    session = env(FakeExtractor(VALID_DOC))
    path = upload(settings, make_pdf)

    result = run(path, save_to_db=True)

    payload = result.get()
    assert payload["saved_to_db"] is True
    assert payload["document"]["document_type"] == "invoice"
    [row] = session.merged
    assert str(row.id) == result.id  # same UUID as the Celery task
    assert row.filename == "factura.pdf"
    assert (row.llm_provider, row.llm_model) == ("fake", "fake-model")
    assert not path.exists()


def test_a_scanned_pdf_is_read_by_the_models_vision(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    path = upload(settings, make_pdf, pages=["", ""])
    sent = path.read_bytes()

    result = run(path, save_to_db=False)

    assert result.successful(), result.result
    assert (result.result["source"], result.result["page_count"]) == ("scan", 2)
    assert extractor.texts == [] and extractor.files == [(sent, "application/pdf")]  # the whole file
    assert not path.exists()


def test_a_pdf_whose_pages_are_mostly_scans_is_read_by_vision(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)

    result = run(upload(settings, make_pdf, pages=[INVOICE_TEXT, "", ""]), save_to_db=False)

    assert result.result["source"] == "scan" and extractor.files[0][1] == "application/pdf"


def test_a_pdf_with_text_is_still_read_as_text(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)

    result = run(upload(settings, make_pdf, pages=[INVOICE_TEXT, INVOICE_TEXT, ""]), save_to_db=False)

    assert result.result["source"] == "text" and extractor.files == []
    assert "Page 1" in extractor.texts[0]


def test_invalid_llm_output_fails_without_retrying(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(LLMExtractionError("LLM output does not match DocumentSchema"))
    env(extractor)
    path = upload(settings, make_pdf)

    result = run(path, save_to_db=True)

    assert result.failed()
    assert extractor.calls == 1
    assert not path.exists()


def test_transient_llm_error_is_retried_and_the_file_kept_until_the_end(
    env: Any, settings: Settings, make_pdf: MakePdf
) -> None:
    extractor = FakeExtractor(LLMTransientError("429"), LLMTransientError("503"), VALID_DOC)
    env(extractor)
    path = upload(settings, make_pdf)

    result = run(path, save_to_db=False)

    assert result.successful()
    assert extractor.calls == 3  # two retries, then success: the PDF had to survive the retries
    assert not path.exists()


def test_transient_error_gives_up_after_max_retries_and_deletes_the_file(
    env: Any, settings: Settings, make_pdf: MakePdf
) -> None:
    extractor = FakeExtractor(LLMTransientError("429"))
    env(extractor)
    path = upload(settings, make_pdf)

    result = run(path, save_to_db=False)

    assert result.failed()
    assert extractor.calls == tasks.process_document.max_retries + 1
    assert not path.exists()


def test_paths_outside_the_upload_dir_are_refused(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    outside = make_pdf([INVOICE_TEXT])  # written next to, not inside, the upload dir

    result = run(outside, save_to_db=False)

    assert result.failed()
    assert extractor.calls == 0
    assert outside.exists()  # never touched


def test_retry_backoff_grows_and_is_capped() -> None:
    delays = [tasks.ProcessDocumentTask.retry_backoff_seconds(n) for n in range(6)]

    assert delays[:4] == [10, 20, 40, 80]
    assert max(delays) == 300


def test_celery_is_configured_for_a_small_server(settings: Settings) -> None:
    conf = celery_module.celery_config(settings)

    assert conf["broker_url"] == settings.celery_broker_url
    assert conf["result_backend"] == settings.celery_result_backend
    assert conf["result_expires"] == settings.result_ttl_seconds
    assert conf["worker_prefetch_multiplier"] == 1
    assert conf["task_track_started"] is True  # lets the UI show "Processing"
    assert conf["task_acks_late"] is True
    assert conf["accept_content"] == ["json"]


def test_persistent_rows_belong_to_the_uploader(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    session = env(FakeExtractor(VALID_DOC))
    owner = uuid.uuid4()

    run(upload(settings, make_pdf), save_to_db=True, user_id=str(owner))

    [row] = session.merged
    assert row.user_id == owner


def test_a_file_removed_by_the_sweep_fails_clearly(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    path = upload(settings, make_pdf)
    path.unlink()  # the orphan sweep got to it first

    result = run(path, save_to_db=False)

    assert result.failed()
    assert type(result.result).__name__ == "UploadExpiredError"
    assert extractor.calls == 0


def test_sweep_task_uses_the_configured_age(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    import os

    env(FakeExtractor(VALID_DOC))
    old, fresh = upload(settings, make_pdf), upload(settings, make_pdf)
    os.utime(old, (1_000, 1_000))

    removed = tasks.sweep_orphan_uploads.apply().get()

    assert removed == 1
    assert not old.exists() and fresh.exists()


def test_beat_runs_the_sweep_every_30_minutes(settings: Settings) -> None:
    schedule = celery_module.celery_config(settings)["beat_schedule"]

    assert schedule["sweep-orphan-uploads"] == {"task": "sweep_orphan_uploads", "schedule": 1800}


def test_beat_reconciles_subscriptions_every_6_hours(settings: Settings) -> None:
    schedule = celery_module.celery_config(settings)["beat_schedule"]

    assert schedule["reconcile-subscriptions"] == {"task": "reconcile_subscriptions", "schedule": 6 * 3600}


def test_reconcile_task_without_payments_configured(env: Any) -> None:
    env(FakeExtractor(VALID_DOC))

    assert tasks.reconcile_subscriptions.apply().get() == 0


def test_reconcile_task_uses_the_paypal_settings(env: Any, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    env(FakeExtractor(VALID_DOC))
    settings.paypal_client_id = "id"
    settings.paypal_client_secret = SecretStr("secret")
    seen: dict[str, Any] = {}

    def fake_reconcile(db: object, client: Any, now: object) -> int:
        seen.update(env=client.env, currency=client.currency)
        return 3

    monkeypatch.setattr(tasks.billing, "reconcile_subscriptions", fake_reconcile)

    assert tasks.reconcile_subscriptions.apply().get() == 3
    assert seen == {"env": "sandbox", "currency": "USD"}


def test_failed_documents_give_their_pages_back(
    env: Any, settings: Settings, make_pdf: MakePdf, monkeypatch: pytest.MonkeyPatch
) -> None:
    refunded: list[str] = []

    def refund_usage(db: Any, task_id: str) -> int:
        refunded.append(task_id)
        return 1

    monkeypatch.setattr(tasks.accounts, "refund_usage", refund_usage)
    env(FakeExtractor(LLMExtractionError("not an invoice"), VALID_DOC))

    failed = run(upload(settings, make_pdf), save_to_db=False)
    ok = run(upload(settings, make_pdf), save_to_db=False)

    assert failed.failed() and ok.successful()
    assert refunded == [failed.id]  # only the failed one


def test_a_refund_problem_never_hides_the_processing_error(
    env: Any, settings: Settings, make_pdf: MakePdf, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(db: object, task_id: str) -> int:
        raise RuntimeError("database down")

    monkeypatch.setattr(tasks.accounts, "refund_usage", broken)
    env(FakeExtractor(LLMExtractionError("not an invoice")))

    result = run(upload(settings, make_pdf), save_to_db=False)

    assert result.failed() and "not an invoice" in str(result.result)


def test_worker_children_get_a_memory_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    import resource

    calls: list[tuple[int, tuple[int, int]]] = []
    monkeypatch.setattr(resource, "setrlimit", lambda kind, limits: calls.append((kind, limits)))

    tasks.limit_child_memory()

    assert calls == [(resource.RLIMIT_DATA, (tasks.TASK_MEMORY_LIMIT_BYTES, tasks.TASK_MEMORY_LIMIT_BYTES))]


def test_a_refused_memory_ceiling_only_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    import resource

    def refuse(kind: int, limits: tuple[int, int]) -> None:
        raise ValueError("not allowed")

    monkeypatch.setattr(resource, "setrlimit", refuse)

    tasks.limit_child_memory()

    assert "memory limit" in caplog.text


def test_tasks_have_time_limits(settings: Settings) -> None:
    config = celery_module.celery_config(settings)

    assert (config["task_soft_time_limit"], config["task_time_limit"]) == (300, 330)


def test_a_bomb_that_reaches_the_worker_fails_cleanly(env: Any, settings: Settings) -> None:
    from tests.test_storage import pdf_with_stream

    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    path = settings.upload_dir / f"{uuid.uuid4()}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_with_stream(b" " * (40 * 1024 * 1024)))

    result = run(path, save_to_db=False)

    assert result.failed() and "DecompressionBombError" in type(result.result).__name__
    assert extractor.calls == 0 and not path.exists()


def test_beat_writes_a_database_heartbeat_every_6_hours(settings: Settings) -> None:
    schedule = celery_module.celery_config(settings)["beat_schedule"]

    assert schedule["database-heartbeat"] == {"task": "database_heartbeat", "schedule": 6 * 3600}


def test_heartbeat_task_records_a_beat(env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    session = env(FakeExtractor(VALID_DOC))
    seen: list[Any] = []

    def beat(db: Any, now: Any) -> int:
        seen.append((db, now))
        return 7

    monkeypatch.setattr(tasks.heartbeat, "beat", beat)

    assert tasks.database_heartbeat.apply().get() == 7
    assert seen and seen[0][0] is session


def stored(settings: Settings, data: bytes, name: str) -> Path:
    return save_stream(io.BytesIO(data), name, upload_dir=settings.upload_dir, max_bytes=10**7).path


def test_an_xml_e_invoice_is_sent_as_clean_text(env: Any, settings: Settings) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    xml = b"<?xml version='1.0'?><Invoice><Total>980560</Total><Signature><Value>abc</Value></Signature></Invoice>"
    path = stored(settings, xml, "factura.xml")

    result = run(path, save_to_db=False)

    assert result.successful(), result.result
    assert (result.result["source"], result.result["page_count"]) == ("xml", 1)
    assert "<Total>980560</Total>" in extractor.texts[0] and "Signature" not in extractor.texts[0]
    assert not path.exists()


def test_a_photo_is_sent_to_the_models_vision_as_a_clean_jpeg(env: Any, settings: Settings) -> None:
    from PIL import Image

    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    buffer = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(buffer, "PNG")
    path = stored(settings, buffer.getvalue(), "boleta.png")

    result = run(path, save_to_db=False)

    assert (result.result["source"], result.result["page_count"]) == ("photo", 1)
    [(data, mime)] = extractor.files
    assert mime == "image/jpeg" and data.startswith(b"\xff\xd8\xff")
    assert not path.exists()


def test_a_broken_photo_fails_and_gives_its_page_back(
    env: Any, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    refunded: list[str] = []

    def refund_usage(db: Any, task_id: str) -> int:
        refunded.append(task_id)
        return 1

    monkeypatch.setattr(tasks.accounts, "refund_usage", refund_usage)
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)

    result = run(stored(settings, b"\xff\xd8\xff" + b"garbage" * 200, "boleta.jpg"), save_to_db=False)

    assert result.failed() and refunded == [result.id] and extractor.calls == 0
