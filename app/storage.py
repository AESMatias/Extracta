"""Upload storage on the shared `/tmp_uploads` volume.

`save_stream()` copies an upload to disk in fixed-size chunks, so a 50 MB PDF
never sits in RAM (2 GB server). Files get server-generated names; the user's
filename is kept only for display, never used to build a path.
`delete_file()` is what the worker calls when a task finishes.
"""

import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

CHUNK_SIZE = 64 * 1024  # 64 KB per read/write: constant memory whatever the file size
_HEADER_WINDOW = 1024  # the PDF spec allows the header anywhere in the first 1024 bytes
_PDF_MAGIC = b"%PDF-"
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_MAX_NAME_LENGTH = 255  # matches documents.filename in the database


class UploadError(ValueError):
    """Base class for uploads the user must fix (shown back to them)."""


class NotAPdfError(UploadError):
    pass


class UploadTooLargeError(UploadError):
    pass


class ReadableStream(Protocol):
    def read(self, size: int = ..., /) -> bytes | None: ...


@dataclass(frozen=True)
class StoredFile:
    id: uuid.UUID
    path: Path
    original_name: str
    size_bytes: int


def save_stream(stream: ReadableStream, filename: str | None, *, upload_dir: Path, max_bytes: int) -> StoredFile:
    """Write `stream` to `upload_dir` chunk by chunk, validating size and PDF header on the way."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    final_path = upload_dir / f"{file_id}.pdf"
    # Write to ".part" first and rename at the end, so the worker never sees a half-written file.
    part_path = upload_dir / f"{file_id}.pdf.part"

    size = 0
    head = b""
    header_checked = False
    try:
        with part_path.open("xb") as out:
            while chunk := stream.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError(f"file is larger than {max_bytes // (1024 * 1024)} MB")
                if not header_checked:
                    head += chunk[: _HEADER_WINDOW - len(head)]
                    if len(head) >= _HEADER_WINDOW:
                        _require_pdf_header(head)
                        header_checked = True
                out.write(chunk)
        if not header_checked:  # files shorter than the header window
            _require_pdf_header(head)
        part_path.rename(final_path)
    except BaseException:
        part_path.unlink(missing_ok=True)  # never leave partial or rejected files behind
        raise

    return StoredFile(id=file_id, path=final_path, original_name=display_name(filename), size_bytes=size)


def _require_pdf_header(head: bytes) -> None:
    # Check the bytes, not the extension: a renamed image or script still ends in ".pdf".
    if _PDF_MAGIC not in head:
        raise NotAPdfError("file is not a PDF")


def display_name(filename: str | None) -> str:
    """Return the user's filename, safe to store and show; never use it as a path."""
    name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]  # drop any directory part
    name = _CONTROL_CHARS.sub("", name).strip()
    return name[:_MAX_NAME_LENGTH] if name else "document.pdf"


def delete_file(path: Path, *, upload_dir: Path) -> bool:
    """Delete an uploaded file. Returns False if it was already gone."""
    resolved = path.resolve()
    if not resolved.is_relative_to(upload_dir.resolve()):
        raise ValueError(f"refusing to delete {path}: outside {upload_dir}")
    try:
        resolved.unlink()
    except FileNotFoundError:
        return False
    return True


def sweep_orphans(upload_dir: Path, *, max_age_seconds: float, now: float | None = None) -> list[Path]:
    """Delete uploads older than `max_age_seconds` (e.g. left behind by a worker killed mid-task).

    Only files this module creates (`<uuid>.pdf` and `<uuid>.pdf.part`) are touched.
    """
    if not upload_dir.is_dir():
        return []
    cutoff = (time.time() if now is None else now) - max_age_seconds
    removed: list[Path] = []
    for path in upload_dir.iterdir():
        if not (path.name.endswith(".pdf") or path.name.endswith(".pdf.part")) or not path.is_file():
            continue
        try:
            uuid.UUID(path.name.split(".", 1)[0])
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed.append(path)
        except (ValueError, FileNotFoundError):  # not ours, or deleted meanwhile by its task
            continue
    return removed
