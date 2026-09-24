"""Shared pytest fixtures."""

from collections.abc import Callable
from pathlib import Path

import pytest


def build_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one text page per item ("" makes a page with no text layer).

    Uses the built-in Helvetica font with WinAnsi encoding, so Latin-1 text such as
    "Factura electrónica" round-trips. Lines are split on "\\n".
    """
    page_count = len(pages)
    # Object numbers: 1 catalog, 2 page tree, 3 font, then (page, content) pairs.
    page_ids = [4 + 2 * i for i in range(page_count)]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % i for i in page_ids) + b"] /Count %d >>" % page_count,
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    for page_id, text in zip(page_ids, pages, strict=True):
        content = b""
        if text:
            lines = [
                line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")
                for line in text.split("\n")
            ]
            content = b"BT /F1 12 Tf 72 720 Td 14 TL " + b" ".join(b"(" + line + b") '" for line in lines) + b" ET"
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (page_id + 1)
        )
        objects[page_id + 1] = b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_at)
    return bytes(out)


@pytest.fixture
def make_pdf(tmp_path: Path) -> Callable[[list[str]], Path]:
    """Return a function that writes a PDF with the given page texts and returns its path."""
    counter = 0

    def _make(pages: list[str]) -> Path:
        nonlocal counter
        counter += 1
        path = tmp_path / f"generated-{counter}.pdf"
        path.write_bytes(build_pdf(pages))
        return path

    return _make
