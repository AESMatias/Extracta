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

    def extract(self, text: str) -> DocumentSchema:
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


def run(path: Path, save_to_db: bool) -> Any:
    # apply() runs the task in-process (no broker, no worker), including its retries.
    return tasks.process_document.apply(args=[str(path), "factura.pdf", save_to_db], task_id=str(uuid.uuid4()))


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


def test_scanned_pdf_fails_and_the_file_is_still_deleted(env: Any, settings: Settings, make_pdf: MakePdf) -> None:
    extractor = FakeExtractor(VALID_DOC)
    env(extractor)
    path = upload(settings, make_pdf, pages=["", ""])

    result = run(path, save_to_db=False)

    assert result.failed()
    assert "scanned" in str(result.result)
    assert extractor.calls == 0  # the LLM was never paid for an empty document
    assert not path.exists()


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
