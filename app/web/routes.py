"""Document API: upload PDFs, follow their tasks, list saved documents and download exports.

Every route needs a signed-in account. Uploads are limited by the account's plan: files per
upload, size per file, persistent mode, and PDFs per rolling 24 hours.
"""

import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from flask import Blueprint, Response, current_app, request, stream_with_context
from pydantic import ValidationError
from sqlalchemy import delete, select

from app import accounts
from app.db import session_scope, utcnow
from app.export import (
    ExportItem,
    UnifiedExportRequest,
    individual_csv,
    individual_json,
    individual_xlsx,
    unified_csv,
    unified_json,
    unified_xlsx,
)
from app.models import Document
from app.schemas import summarize_validation_error
from app.storage import UploadError, delete_file, display_name, save_stream
from app.web.ownership import TaskOwnership
from app.web.queue import TaskQueue
from app.web.security import ApiError, UploadLock, require_active, require_user, settings

api = Blueprint("api", __name__, url_prefix="/api")

MAX_FILES_PER_UPLOAD = 50  # absolute cap; each plan allows fewer
MAX_STATUS_BATCH = 100
# JSON export bodies are parsed in memory: cap them far below the multi-file upload limit.
MAX_EXPORT_BODY_BYTES = 10 * 1024 * 1024
_TRUE_VALUES = {"1", "true", "on", "yes"}
Body = tuple[dict[str, Any], int]


def _queue() -> TaskQueue:
    queue: TaskQueue = current_app.extensions["task_queue"]
    return queue


def _ownership() -> TaskOwnership:
    ownership: TaskOwnership = current_app.extensions["task_ownership"]
    return ownership


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


@api.get("/health")
def health() -> Body:
    return {"status": "ok"}, 200


# --------------------------------------------------------------------------- upload


@api.post("/upload")
def upload() -> Body:
    now = utcnow()
    # Check the account before touching the body: a signed-out or over-quota request is refused
    # without parsing (and spooling to disk) megabytes of PDFs.
    with session_scope() as db:
        user = require_user(db)
        require_active(user)
        plan = accounts.current_plan(user, now)
        quota = accounts.usage(db, user, now)
        user_id = user.id
    if quota.remaining == 0:
        raise ApiError(
            429,
            f"You reached your limit of {quota.limit} PDFs in 24 hours.",
            next_slot_at=quota.next_slot_at.isoformat() if quota.next_slot_at else None,
            upgrade=True,
        )

    files = [file for file in request.files.getlist("files") if file.filename]
    if not files:
        raise ApiError(400, "Send at least one PDF in the 'files' field.")
    if len(files) > min(plan.max_files_per_upload, MAX_FILES_PER_UPLOAD):
        raise ApiError(400, f"Your {plan.name} plan allows {plan.max_files_per_upload} files per upload.", upgrade=True)
    raw_mode = request.args.get("save_to_db") or request.form.get("save_to_db") or ""
    save_to_db = raw_mode.strip().lower() in _TRUE_VALUES  # default: process only
    if save_to_db and not plan.can_save_to_db:
        raise ApiError(403, "Saving documents to the database is available on paid plans.", upgrade=True)

    lock: UploadLock = current_app.extensions["upload_lock"]
    if not lock.acquire(user_id):
        raise ApiError(409, "Another upload from your account is still in progress. Wait for it to finish.")
    config = settings()
    max_bytes = min(plan.max_file_mb, config.max_upload_mb) * 1024 * 1024
    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    try:
        for file in files:
            if len(accepted) >= quota.remaining:
                rejected.append({"filename": display_name(file.filename), "error": "Daily limit reached"})
                continue
            try:
                stored = save_stream(file.stream, file.filename, upload_dir=config.upload_dir, max_bytes=max_bytes)
            except UploadError as exc:  # not a PDF, too large: report it and keep going with the rest
                rejected.append({"filename": display_name(file.filename), "error": str(exc)})
                continue
            try:
                task_id = _queue().enqueue(stored.path, stored.original_name, save_to_db, str(user_id))
            except Exception:
                delete_file(stored.path, upload_dir=config.upload_dir)  # nobody will process it: free the disk
                raise
            accepted.append({"task_id": task_id, "filename": stored.original_name})

        if accepted:
            task_ids = [task["task_id"] for task in accepted]
            with session_scope() as db:
                accounts.record_usage(db, user_id, task_ids, now)
            _ownership().add(str(user_id), task_ids)
    finally:
        lock.release(user_id)

    body = {
        "save_to_db": save_to_db,
        "tasks": accepted,
        "rejected": rejected,
        "usage": {"used": quota.used + len(accepted), "limit": quota.limit},
    }
    return body, 202 if accepted else 400


# --------------------------------------------------------------------------- task status


def _status_body(task_id: str) -> dict[str, Any]:
    status = _queue().status(task_id)
    body: dict[str, Any] = {"task_id": task_id, "status": status.status}
    if status.result is not None:
        body["result"] = status.result
    if status.error is not None:
        body["error"] = status.error
    return body


@api.get("/tasks/<task_id>")
def task_status(task_id: str) -> Body:
    with session_scope() as db:
        owner = str(require_user(db).id)
    if not _is_uuid(task_id) or not _ownership().owns(owner, task_id):
        raise ApiError(404, "Task not found.")  # 404, not 403: do not even confirm that the task exists
    return _status_body(task_id), 200


@api.post("/tasks/status")
def task_statuses() -> Body:
    """Status of many tasks in one request (the dashboard polls this every few seconds)."""
    payload = request.get_json(silent=True) or {}
    task_ids = payload.get("task_ids")
    if not isinstance(task_ids, list) or not task_ids or len(task_ids) > MAX_STATUS_BATCH:
        raise ApiError(400, f"Send 1 to {MAX_STATUS_BATCH} task ids in 'task_ids'.")
    with session_scope() as db:
        owner = str(require_user(db).id)
    ownership = _ownership()
    tasks = [
        _status_body(task_id)
        if isinstance(task_id, str) and _is_uuid(task_id) and ownership.owns(owner, task_id)
        else {"task_id": str(task_id), "status": "not_found"}
        for task_id in task_ids
    ]
    return {"tasks": tasks}, 200


# --------------------------------------------------------------------------- saved documents


@api.get("/documents")
def list_documents() -> Body:
    with session_scope() as db:
        user = require_user(db)
        rows = db.execute(
            select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc()).limit(200)
        ).scalars()
        documents = [
            {
                "id": str(row.id),
                "filename": row.filename,
                "document_type": row.document_type,
                "title": row.title,
                "summary": row.summary,
                "created_at": row.created_at.isoformat(),
                "document": row.data,
            }
            for row in rows
        ]
    return {"documents": documents}, 200


@api.delete("/documents/<document_id>")
def delete_document(document_id: str) -> Body:
    if not _is_uuid(document_id):
        raise ApiError(404, "Document not found.")
    with session_scope() as db:
        user = require_user(db)
        result = db.execute(delete(Document).where(Document.id == uuid.UUID(document_id), Document.user_id == user.id))
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise ApiError(404, "Document not found.")
    return {"deleted": document_id}, 200


# --------------------------------------------------------------------------- export (CSV, XLSX, JSON)

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_MIMETYPES = {"csv": "text/csv", "xlsx": _XLSX_MIME, "json": "application/json"}


def _attachment(filename: str) -> str:
    # ASCII fallback for old clients, plus the exact UTF-8 name (RFC 6266) for modern browsers.
    ascii_name = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9.-]", "_", filename)).strip("_") or "export"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def _download(content: Iterator[str] | bytes, fmt: str, filename: str) -> Response:
    body = stream_with_context(content) if isinstance(content, Iterator) else content  # CSV streams row by row
    return Response(body, mimetype=_MIMETYPES[fmt], headers={"Content-Disposition": _attachment(filename)})


def _export_payload(fmt: str) -> Any:
    if fmt not in _MIMETYPES:
        raise ApiError(404, "Unknown export format. Use csv, xlsx or json.")
    with session_scope() as db:
        require_user(db)
    request.max_content_length = MAX_EXPORT_BODY_BYTES  # checked before the body is read: larger -> 413
    payload = request.get_json(silent=True)
    if payload is None:
        raise ApiError(400, "Send the documents as a JSON body.")
    return payload


def _invalid(exc: ValidationError) -> ApiError:
    return ApiError(400, "Invalid document data.", details=summarize_validation_error(exc))


@api.post("/export/<fmt>/individual")
def export_individual(fmt: str) -> Response:
    payload = _export_payload(fmt)
    try:
        item = ExportItem.model_validate(payload)  # the browser's JSON is untrusted: validate it again
    except ValidationError as exc:
        raise _invalid(exc) from None

    stem = re.sub(r"\.pdf$", "", display_name(item.filename), flags=re.IGNORECASE) or "document"
    content: Iterator[str] | bytes
    if fmt == "csv":
        content = individual_csv(item.document, filename=item.filename)
    elif fmt == "xlsx":
        content = individual_xlsx(item.document, filename=item.filename)
    else:
        content = individual_json(item)
    return _download(content, fmt, f"{stem}.{fmt}")


@api.post("/export/<fmt>/unified")
def export_unified(fmt: str) -> Response:
    payload = _export_payload(fmt)
    try:
        export = UnifiedExportRequest.model_validate(payload)
    except ValidationError as exc:
        raise _invalid(exc) from None

    content: Iterator[str] | bytes
    if fmt == "csv":
        content = unified_csv(export.items)
    elif fmt == "xlsx":
        content = unified_xlsx(export.items)
    else:
        content = unified_json(export.items)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return _download(content, fmt, f"documents-{stamp}.{fmt}")
