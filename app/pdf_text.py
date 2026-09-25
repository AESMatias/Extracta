"""Text extraction from digital PDFs with pdfplumber.

Pages are parsed one at a time and released right after, so a long PDF does
not pile up in the worker's memory. Reading stops as soon as the character
budget for the LLM is spent: the rest of the file is never parsed.
"""

from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

# ~120k tokens: the whole text of the largest PDF a plan accepts (150 pages at ~3,000 characters
# each). Usage is charged per page, so every page paid for is read; this only guards the LLM cost.
MAX_TEXT_CHARS = 450_000
# Scans often carry a page number or a stamp as real text; below this there is nothing to extract.
MIN_TEXT_CHARS = 20
_SEPARATOR = "\n\n"


class NoTextLayerError(ValueError):
    """The PDF has no extractable text (typically a scan); it would need OCR."""


class UnreadablePdfError(ValueError):
    """The file is corrupted, encrypted or otherwise not parseable."""


@dataclass(frozen=True)
class ExtractedText:
    text: str  # "--- Page N ---" markers help the LLM cite and separate pages
    page_count: int
    pages_read: int
    truncated: bool


def extract_text(path: Path, *, max_chars: int = MAX_TEXT_CHARS) -> ExtractedText:
    blocks: list[str] = []
    length = 0
    content_chars = 0  # visible characters of the document itself, page markers excluded
    truncated = False
    pages_read = 0

    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = (page.extract_text() or "").strip()
                page.close()  # release the parsed page objects before reading the next one
                pages_read += 1
                if not page_text:
                    continue  # blank or image-only page
                content_chars += sum(not c.isspace() for c in page_text)

                block = (_SEPARATOR if blocks else "") + f"--- Page {pages_read} ---\n{page_text}"
                if length + len(block) >= max_chars:
                    blocks.append(block[: max_chars - length])
                    truncated = length + len(block) > max_chars
                    break
                blocks.append(block)
                length += len(block)
    except PdfminerException as exc:
        raise UnreadablePdfError(f"cannot read PDF: {exc}") from exc

    text = "".join(blocks)
    if content_chars < MIN_TEXT_CHARS:
        raise NoTextLayerError("no extractable text: the PDF looks scanned and would need OCR")
    return ExtractedText(text=text, page_count=page_count, pages_read=pages_read, truncated=truncated)
