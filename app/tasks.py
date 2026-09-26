"""The background task that processes one upload (the Celery app lives in app/celery_app.py).

Pipeline: read the file (PDF text, cleaned XML, or the image or scanned PDF itself for the LLM's
vision; see app/formats.py) -> LLM -> save to the database only if `save_to_db` -> return the data.
Celery stores the returned data in the Redis result backend for RESULT_TTL_SECONDS, in both
modes, so the web app can show and export it. The file is deleted when the task finishes,
whatever the outcome; only a pending retry keeps it.

Worker (see docker-compose.yml):  celery -A app.tasks:celery_app worker --beat --concurrency=1
"""

import logging
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from celery import Task
from celery.signals import worker_process_init
from sqlalchemy.exc import OperationalError

from app import accounts, billing, heartbeat
from app.celery_app import (
    DATABASE_HEARTBEAT_TASK,
    PROCESS_DOCUMENT_TASK,
    RECONCILE_SUBSCRIPTIONS_TASK,
    SWEEP_ORPHANS_TASK,
    celery_app,
)
from app.config import get_settings
from app.db import session_scope, utcnow
from app.formats import IMAGE_FORMATS, format_of, prepare_image, xml_text
from app.llm import DocumentExtractor, LLMTransientError, build_extractor
from app.models import Document
from app.pdf_text import MAX_TEXT_CHARS, NoTextLayerError, extract_text
from app.storage import check_expansion, count_pages, delete_file, sweep_orphans

log = logging.getLogger(__name__)

# Data memory each worker child may use. A hostile PDF that gets past check_expansion raises
# MemoryError inside the task (which then fails cleanly, gives the pages back and deletes the file)
# instead of making the kernel kill the whole worker. A child uses ~90 MB at rest.
TASK_MEMORY_LIMIT_BYTES = 450 * 1024 * 1024


@worker_process_init.connect
def limit_child_memory(**_: object) -> None:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_DATA, (TASK_MEMORY_LIMIT_BYTES, TASK_MEMORY_LIMIT_BYTES))
    except (ImportError, ValueError, OSError):  # not Linux, or not allowed: keep the container limit only
        log.warning("Could not set the per-task memory limit")


class UploadExpiredError(RuntimeError):
    """The PDF was removed by the orphan sweep before the queue reached it."""


@lru_cache
def get_extractor() -> DocumentExtractor:
    # One LLM client per worker process, reused across tasks.
    return build_extractor(get_settings())


def run_pipeline(
    path: Path,
    filename: str,
    *,
    save_to_db: bool,
    task_id: uuid.UUID,
    extractor: DocumentExtractor,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    if not path.exists():
        raise UploadExpiredError("the uploaded file is no longer on disk")
    fmt = format_of(path)
    truncated = False
    if fmt == "xml":
        text, truncated = xml_text(path, max_chars=MAX_TEXT_CHARS)
        document, page_count, source = extractor.extract(text), 1, "xml"
    elif fmt in IMAGE_FORMATS:
        document, page_count, source = extractor.extract_file(prepare_image(path), "image/jpeg"), 1, "image"
    else:
        check_expansion(path)  # defense in depth: the upload already checked it
        try:
            extracted = extract_text(path)
        except NoTextLayerError:
            extracted = None
        # A scan, or a PDF whose pages are mostly images: the model reads the file itself.
        if extracted is None or 2 * extracted.pages_without_text > extracted.pages_read:
            page_count = extracted.page_count if extracted else count_pages(path)
            document, source = extractor.extract_file(path.read_bytes(), "application/pdf"), "scan"
        else:
            page_count, truncated = extracted.page_count, extracted.truncated
            document, source = extractor.extract(extracted.text), "text"

    if save_to_db:
        row = Document.from_extraction(
            task_id=task_id,
            filename=filename,
            extraction=document,
            llm_provider=extractor.provider,
            llm_model=extractor.model,
            user_id=user_id,
        )
        with session_scope() as session:
            session.merge(row)  # merge, not add: a redelivered task updates its row instead of failing

    return {
        "task_id": str(task_id),
        "filename": filename,
        "saved_to_db": save_to_db,
        "page_count": page_count,
        "truncated": truncated,
        "source": source,  # text, xml, image or scan
        "llm_provider": extractor.provider,
        "llm_model": extractor.model,
        "document": document.model_dump(mode="json"),
    }


def give_pages_back(task_id: str) -> None:
    """Return the pages of a PDF that could not be processed to its owner's quota."""
    try:
        with session_scope() as session:
            accounts.refund_usage(session, task_id)
    except Exception:  # never hide the processing error behind a refund problem
        log.exception("Could not give back the pages of task %s", task_id)


class ProcessDocumentTask(Task):  # type: ignore[misc]
    max_retries = 3
    acks_late = True

    @staticmethod
    def retry_backoff_seconds(retries: int) -> int:
        # 10 s, 20 s, 40 s, 80 s... capped at 5 minutes: gives a rate limit time to reset.
        return int(min(10 * 2**retries, 300))


@celery_app.task(bind=True, base=ProcessDocumentTask, name=PROCESS_DOCUMENT_TASK)
def process_document(
    self: ProcessDocumentTask, file_path: str, filename: str, save_to_db: bool, user_id: str | None = None
) -> dict[str, Any]:
    settings = get_settings()
    path = Path(file_path)
    if not path.resolve().is_relative_to(settings.upload_dir.resolve()):
        raise ValueError("refusing to process a file outside the upload directory")

    will_retry = False
    try:
        return run_pipeline(
            path,
            filename,
            save_to_db=save_to_db,
            task_id=uuid.UUID(self.request.id),
            extractor=get_extractor(),
            user_id=uuid.UUID(user_id) if user_id else None,
        )
    except (LLMTransientError, OperationalError) as exc:  # rate limit, provider outage, database unreachable
        if self.request.retries < self.max_retries:
            will_retry = True
            raise self.retry(exc=exc, countdown=self.retry_backoff_seconds(self.request.retries)) from None
        give_pages_back(self.request.id)
        raise
    except Exception:
        give_pages_back(self.request.id)  # scanned, damaged, invalid AI answer: the user does not pay
        raise
    finally:
        if not will_retry:
            delete_file(path, upload_dir=settings.upload_dir)  # success or final failure: free the disk


@celery_app.task(name=SWEEP_ORPHANS_TASK)
def sweep_orphan_uploads() -> int:
    """Periodic cleanup (see beat_schedule): PDFs a crashed task never deleted."""
    settings = get_settings()
    removed = sweep_orphans(settings.upload_dir, max_age_seconds=settings.orphan_max_age_hours * 3600)
    return len(removed)


@celery_app.task(name=RECONCILE_SUBSCRIPTIONS_TASK)
def reconcile_subscriptions() -> int:
    """Periodic check (see beat_schedule): subscriptions whose renewal a lost webhook never applied."""
    settings = get_settings()
    if not (settings.paypal_client_id and settings.paypal_client_secret):
        return 0  # payments are not configured
    from app.web.paypal import PayPalClient  # only needed here: keeps the worker's imports lean

    client = PayPalClient(
        client_id=settings.paypal_client_id,
        client_secret=settings.paypal_client_secret.get_secret_value(),
        env=settings.paypal_env,
        currency="USD",
    )
    with session_scope() as db:
        return billing.reconcile_subscriptions(db, client, utcnow())


@celery_app.task(name=DATABASE_HEARTBEAT_TASK)
def database_heartbeat() -> int:
    """Periodic write (see beat_schedule) so the database never looks idle, even with no users."""
    with session_scope() as db:
        return heartbeat.beat(db, utcnow())
