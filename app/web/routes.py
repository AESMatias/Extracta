"""HTTP API: upload PDFs, poll task status, download exports (CSV, XLSX, JSON)."""

import re
import secrets
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from flask import Blueprint, Response, current_app, request, session, stream_with_context
from pydantic import ValidationError

from app.config import Settings
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
from app.schemas import summarize_validation_error
from app.storage import UploadError, delete_file, display_name, save_stream
from app.web.ownership import TaskOwnership
from app.web.queue import TaskQueue

api = Blueprint("api", __name__)

MAX_FILES_PER_UPLOAD = 50
_OWNER_KEY = "owner"
_TRUE_VALUES = {"1", "true", "on", "yes"}
Body = tuple[dict[str, Any], int]


def _settings() -> Settings:
    settings: Settings = current_app.extensions["settings"]
    return settings


def _queue() -> TaskQueue:
    queue: TaskQueue = current_app.extensions["task_queue"]
    return queue


def _ownership() -> TaskOwnership:
    ownership: TaskOwnership = current_app.extensions["task_ownership"]
    return ownership


def _owner(*, create: bool) -> str | None:
    """This browser's random owner token, kept in the signed session cookie."""
    owner = session.get(_OWNER_KEY)
    if owner is None and create:
        owner = secrets.token_urlsafe(32)
        session[_OWNER_KEY] = owner
    return owner


# --------------------------------------------------------------------------- upload


@api.post("/upload")
def upload() -> Body:
    files = [file for file in request.files.getlist("files") if file.filename]
    if not files:
        return {"error": "Send at least one PDF in the 'files' field."}, 400
    if len(files) > MAX_FILES_PER_UPLOAD:
        return {"error": f"Send at most {MAX_FILES_PER_UPLOAD} files per upload."}, 400

    settings = _settings()
    save_to_db = (request.form.get("save_to_db") or "").strip().lower() in _TRUE_VALUES  # default: ephemeral
    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []

    for file in files:
        try:
            stored = save_stream(
                file.stream, file.filename, upload_dir=settings.upload_dir, max_bytes=settings.max_upload_bytes
            )
        except UploadError as exc:  # not a PDF, too large: report it and keep going with the rest
            rejected.append({"filename": display_name(file.filename), "error": str(exc)})
            continue
        try:
            task_id = _queue().enqueue(stored.path, stored.original_name, save_to_db)
        except Exception:
            delete_file(stored.path, upload_dir=settings.upload_dir)  # nobody will process it: free the disk
            raise
        accepted.append({"task_id": task_id, "filename": stored.original_name})

    if accepted:
        owner = _owner(create=True)
        assert owner is not None
        _ownership().add(owner, [task["task_id"] for task in accepted])

    return {"save_to_db": save_to_db, "tasks": accepted, "rejected": rejected}, 202 if accepted else 400


# --------------------------------------------------------------------------- task status


@api.get("/tasks/<task_id>")
def task_status(task_id: str) -> Body:
    not_found = {"error": "Task not found."}, 404
    try:
        uuid.UUID(task_id)
    except ValueError:
        return not_found

    owner = _owner(create=False)
    if owner is None or not _ownership().owns(owner, task_id):
        return not_found  # 404, not 403: do not even confirm that the task exists

    status = _queue().status(task_id)
    body: dict[str, Any] = {"task_id": task_id, "status": status.status}
    if status.result is not None:
        body["result"] = status.result
    if status.error is not None:
        body["error"] = status.error
    return body, 200


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


def _invalid(exc: ValidationError) -> Body:
    return {"error": "Invalid document data.", "details": summarize_validation_error(exc)}, 400


def _not_found() -> Body:
    return {"error": "Unknown export format. Use csv, xlsx or json."}, 404


@api.post("/export/<fmt>/individual")
def export_individual(fmt: str) -> Response | Body:
    if fmt not in _MIMETYPES:
        return _not_found()
    payload = request.get_json(silent=True)
    if payload is None:
        return {"error": "Send the document as a JSON body."}, 400
    try:
        item = ExportItem.model_validate(payload)  # the browser's JSON is untrusted: validate it again
    except ValidationError as exc:
        return _invalid(exc)

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
def export_unified(fmt: str) -> Response | Body:
    if fmt not in _MIMETYPES:
        return _not_found()
    payload = request.get_json(silent=True)
    if payload is None:
        return {"error": "Send the documents as a JSON body."}, 400
    try:
        export = UnifiedExportRequest.model_validate(payload)
    except ValidationError as exc:
        return _invalid(exc)

    content: Iterator[str] | bytes
    if fmt == "csv":
        content = unified_csv(export.items)
    elif fmt == "xlsx":
        content = unified_xlsx(export.items)
    else:
        content = unified_json(export.items)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return _download(content, fmt, f"documents-{stamp}.{fmt}")


@api.app_errorhandler(413)
def request_too_large(_: Exception) -> Body:
    return {"error": "The upload is too large. Send fewer or smaller files."}, 413
