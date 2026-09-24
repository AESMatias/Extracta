"""The background task that processes one uploaded PDF (the Celery app lives in app/celery_app.py).

Pipeline: extract text -> LLM -> save to Supabase only if `save_to_db` -> return the data.
Celery stores the returned data in the Redis result backend for RESULT_TTL_SECONDS, in both
modes, so the web app can show and export it. The PDF is deleted when the task finishes,
whatever the outcome; only a pending retry keeps it.

Worker (see docker-compose.yml):  celery -A app.tasks:celery_app worker --concurrency=1
"""

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from celery import Task
from sqlalchemy.exc import OperationalError

from app.celery_app import PROCESS_DOCUMENT_TASK, celery_app
from app.config import get_settings
from app.db import session_scope
from app.llm import DocumentExtractor, LLMTransientError, build_extractor
from app.models import Document
from app.pdf_text import extract_text
from app.storage import delete_file


@lru_cache
def get_extractor() -> DocumentExtractor:
    # One LLM client per worker process, reused across tasks.
    return build_extractor(get_settings())


def run_pipeline(
    path: Path, filename: str, *, save_to_db: bool, task_id: uuid.UUID, extractor: DocumentExtractor
) -> dict[str, Any]:
    extracted = extract_text(path)  # raises NoTextLayerError before any LLM cost for scans
    document = extractor.extract(extracted.text)

    if save_to_db:
        row = Document.from_extraction(
            task_id=task_id,
            filename=filename,
            extraction=document,
            llm_provider=extractor.provider,
            llm_model=extractor.model,
        )
        with session_scope() as session:
            session.merge(row)  # merge, not add: a redelivered task updates its row instead of failing

    return {
        "task_id": str(task_id),
        "filename": filename,
        "saved_to_db": save_to_db,
        "page_count": extracted.page_count,
        "truncated": extracted.truncated,
        "llm_provider": extractor.provider,
        "llm_model": extractor.model,
        "document": document.model_dump(mode="json"),
    }


class ProcessDocumentTask(Task):  # type: ignore[misc]
    max_retries = 3
    acks_late = True

    @staticmethod
    def retry_backoff_seconds(retries: int) -> int:
        # 10 s, 20 s, 40 s, 80 s... capped at 5 minutes: gives a rate limit time to reset.
        return int(min(10 * 2**retries, 300))


@celery_app.task(bind=True, base=ProcessDocumentTask, name=PROCESS_DOCUMENT_TASK)
def process_document(self: ProcessDocumentTask, file_path: str, filename: str, save_to_db: bool) -> dict[str, Any]:
    settings = get_settings()
    path = Path(file_path)
    if not path.resolve().is_relative_to(settings.upload_dir.resolve()):
        raise ValueError("refusing to process a file outside the upload directory")

    will_retry = False
    try:
        return run_pipeline(
            path, filename, save_to_db=save_to_db, task_id=uuid.UUID(self.request.id), extractor=get_extractor()
        )
    except (LLMTransientError, OperationalError) as exc:  # rate limit, provider outage, database unreachable
        if self.request.retries < self.max_retries:
            will_retry = True
            raise self.retry(exc=exc, countdown=self.retry_backoff_seconds(self.request.retries)) from None
        raise
    finally:
        if not will_retry:
            delete_file(path, upload_dir=settings.upload_dir)  # success or final failure: free the disk
