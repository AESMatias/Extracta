"""How the web app talks to Celery: enqueue a PDF and read a task's status and result.

Celery has many states; the UI needs four. Failures are turned into short messages for the
user, never the raw exception, which can contain file paths or internal details.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from app.celery_app import PROCESS_DOCUMENT_TASK, celery_app

Status = Literal["pending", "processing", "completed", "failed"]

_STATUS_BY_STATE: dict[str, Status] = {
    "PENDING": "pending",  # queued (Celery also reports unknown ids as PENDING)
    "RECEIVED": "pending",
    "STARTED": "processing",
    "RETRY": "processing",  # waiting to retry after a rate limit or outage
    "SUCCESS": "completed",
    "FAILURE": "failed",
    "REVOKED": "failed",
}

# Keyed by exception class name: Celery rebuilds exceptions from JSON, so match by name.
_USER_MESSAGES = {
    "NoTextLayerError": "This PDF has no text layer (it looks scanned). Scanned documents need OCR, not supported yet.",
    "UnreadablePdfError": "This PDF is damaged or password-protected and cannot be read.",
    "LLMTransientError": "The AI service is busy right now. Please upload the document again in a few minutes.",
    "LLMExtractionError": "The document could not be converted into structured data.",
}
DEFAULT_ERROR = "Unexpected error while processing the document."


@dataclass(frozen=True)
class TaskStatus:
    status: Status
    result: dict[str, Any] | None = None
    error: str | None = None


def describe_error(error: object) -> str:
    return _USER_MESSAGES.get(type(error).__name__, DEFAULT_ERROR)


def to_status(state: str, result: Any) -> TaskStatus:
    status = _STATUS_BY_STATE.get(state, "processing")
    if status == "completed":
        return TaskStatus(status=status, result=result)
    if status == "failed":
        return TaskStatus(status=status, error=describe_error(result))
    return TaskStatus(status=status)


class TaskQueue(Protocol):
    def enqueue(self, file_path: Path, filename: str, save_to_db: bool) -> str: ...

    def status(self, task_id: str) -> TaskStatus: ...


class CeleryTaskQueue:
    def enqueue(self, file_path: Path, filename: str, save_to_db: bool) -> str:
        # Sent by name: the web process never imports the task code (pdfplumber, LLM SDKs, SQLAlchemy).
        result = celery_app.send_task(PROCESS_DOCUMENT_TASK, args=[str(file_path), filename, save_to_db])
        return str(result.id)

    def status(self, task_id: str) -> TaskStatus:
        result = celery_app.AsyncResult(task_id)
        return to_status(result.state, result.result)
