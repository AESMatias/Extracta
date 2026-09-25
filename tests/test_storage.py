import io
import tracemalloc
from pathlib import Path

import pytest

from app.storage import (
    CHUNK_SIZE,
    NotAPdfError,
    UploadTooLargeError,
    delete_file,
    display_name,
    save_stream,
    sweep_orphans,
)

PDF_BYTES = b"%PDF-1.7\n" + b"x" * 1000 + b"\n%%EOF\n"
MB = 1024 * 1024
_ZEROS = memoryview(bytes(CHUNK_SIZE))  # reused by FakePdfStream, so the test itself allocates nothing


class FakePdfStream(io.RawIOBase):
    """A readable stream of `size` bytes that never holds more than one chunk in memory."""

    def __init__(self, size: int) -> None:
        self.remaining = size
        self.header = b"%PDF-1.7\n"

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: memoryview) -> int:  # type: ignore[override]
        if self.remaining <= 0:
            return 0
        n = min(len(buffer), self.remaining)
        data = self.header[:n] if self.header else b""
        self.header = self.header[len(data) :]
        buffer[: len(data)] = data
        buffer[len(data) : n] = _ZEROS[: n - len(data)]
        self.remaining -= n
        return n


def files_in(directory: Path) -> list[Path]:
    return sorted(directory.iterdir()) if directory.exists() else []


def test_saves_a_pdf_with_a_server_generated_name(tmp_path: Path) -> None:
    stored = save_stream(io.BytesIO(PDF_BYTES), "factura.pdf", upload_dir=tmp_path, max_bytes=MB)

    assert stored.path == tmp_path / f"{stored.id}.pdf"
    assert stored.path.read_bytes() == PDF_BYTES
    assert stored.size_bytes == len(PDF_BYTES)
    assert stored.original_name == "factura.pdf"
    assert files_in(tmp_path) == [stored.path]  # no leftover .part file


def test_creates_the_upload_dir_if_missing(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"

    stored = save_stream(io.BytesIO(PDF_BYTES), "a.pdf", upload_dir=upload_dir, max_bytes=MB)

    assert stored.path.parent == upload_dir


def test_rejects_a_file_that_is_not_a_pdf(tmp_path: Path) -> None:
    # A renamed image or script: the extension says .pdf, the bytes do not.
    with pytest.raises(NotAPdfError):
        save_stream(io.BytesIO(b"\x89PNG\r\n fake"), "photo.pdf", upload_dir=tmp_path, max_bytes=MB)

    assert files_in(tmp_path) == []


def test_rejects_an_empty_file(tmp_path: Path) -> None:
    with pytest.raises(NotAPdfError):
        save_stream(io.BytesIO(b""), "empty.pdf", upload_dir=tmp_path, max_bytes=MB)

    assert files_in(tmp_path) == []


def test_accepts_a_header_after_leading_junk(tmp_path: Path) -> None:
    # The PDF spec allows the %PDF- header anywhere in the first 1024 bytes.
    stored = save_stream(io.BytesIO(b"\n\n" + PDF_BYTES), "a.pdf", upload_dir=tmp_path, max_bytes=MB)

    assert stored.path.exists()


def test_rejects_a_file_over_the_limit_and_removes_the_partial_file(tmp_path: Path) -> None:
    with pytest.raises(UploadTooLargeError):
        save_stream(FakePdfStream(3 * MB), "big.pdf", upload_dir=tmp_path, max_bytes=2 * MB)

    assert files_in(tmp_path) == []


def test_a_file_exactly_at_the_limit_is_accepted(tmp_path: Path) -> None:
    stored = save_stream(FakePdfStream(2 * MB), "limit.pdf", upload_dir=tmp_path, max_bytes=2 * MB)

    assert stored.size_bytes == 2 * MB


def test_memory_stays_flat_for_a_large_upload(tmp_path: Path) -> None:
    size = 50 * MB
    tracemalloc.start()
    try:
        stored = save_stream(FakePdfStream(size), "large.pdf", upload_dir=tmp_path, max_bytes=size)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert stored.size_bytes == size
    # Only a few chunks may live in memory at once, never the 50 MB file.
    assert peak < 4 * CHUNK_SIZE


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("factura.pdf", "factura.pdf"),
        ("Factura electrónica N° 12.pdf", "Factura electrónica N° 12.pdf"),  # accents kept for display
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\ana\\cv.pdf", "cv.pdf"),
        ("bad\x00name\r\n.pdf", "badname.pdf"),
        ("", "document.pdf"),
        ("   ", "document.pdf"),
        (None, "document.pdf"),
    ],
)
def test_display_name_is_safe_to_show(raw: str | None, expected: str) -> None:
    assert display_name(raw) == expected


def test_display_name_is_truncated_to_255_characters() -> None:
    assert len(display_name("a" * 300 + ".pdf")) == 255


def test_delete_file_removes_it_and_is_idempotent(tmp_path: Path) -> None:
    stored = save_stream(io.BytesIO(PDF_BYTES), "a.pdf", upload_dir=tmp_path, max_bytes=MB)

    assert delete_file(stored.path, upload_dir=tmp_path) is True
    assert not stored.path.exists()
    assert delete_file(stored.path, upload_dir=tmp_path) is False  # already gone: no error


def test_delete_file_refuses_paths_outside_the_upload_dir(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    outside = tmp_path / "important.txt"
    outside.write_text("keep me")

    with pytest.raises(ValueError, match="outside"):
        delete_file(upload_dir / ".." / "important.txt", upload_dir=upload_dir)

    assert outside.exists()


def test_sweep_removes_only_old_uploads_created_by_this_module(tmp_path: Path) -> None:
    import os
    import uuid as uuid_module

    old_pdf = tmp_path / f"{uuid_module.uuid4()}.pdf"
    old_part = tmp_path / f"{uuid_module.uuid4()}.pdf.part"
    fresh = tmp_path / f"{uuid_module.uuid4()}.pdf"
    foreign = tmp_path / "notes.pdf"  # not a name save_stream() creates: never touched
    for path in (old_pdf, old_part, fresh, foreign):
        path.write_bytes(PDF_BYTES)
    for path in (old_pdf, old_part, foreign):
        os.utime(path, (1_000, 1_000))

    removed = sweep_orphans(tmp_path, max_age_seconds=3600, now=1_000 + 7200)

    assert sorted(removed) == sorted([old_pdf, old_part])
    assert fresh.exists() and foreign.exists()


def test_sweep_of_a_missing_directory_does_nothing(tmp_path: Path) -> None:
    assert sweep_orphans(tmp_path / "missing", max_age_seconds=1) == []
