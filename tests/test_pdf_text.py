from collections.abc import Callable
from pathlib import Path

import pytest

from app.pdf_text import NoTextLayerError, UnreadablePdfError, extract_text

MakePdf = Callable[[list[str]], Path]


def test_extracts_text_with_page_markers(make_pdf: MakePdf) -> None:
    path = make_pdf(["Factura electrónica N° 1234\nTotal: $119.000", "Condiciones de pago: 30 días"])

    result = extract_text(path)

    assert result.text == (
        "--- Page 1 ---\nFactura electrónica N° 1234\nTotal: $119.000\n\n--- Page 2 ---\nCondiciones de pago: 30 días"
    )
    assert result.page_count == 2
    assert result.pages_read == 2
    assert result.truncated is False


def test_blank_pages_are_skipped_but_counted(make_pdf: MakePdf) -> None:
    path = make_pdf(["First page with enough text to count.", "", "Third page with enough text to count."])

    result = extract_text(path)

    assert "--- Page 2 ---" not in result.text
    assert "--- Page 3 ---\nThird page" in result.text
    assert result.pages_read == 3


def test_scanned_pdf_without_text_layer_is_rejected(make_pdf: MakePdf) -> None:
    # A scanned document is just images: pdfplumber finds no text on any page.
    path = make_pdf(["", "", ""])

    with pytest.raises(NoTextLayerError, match="scanned"):
        extract_text(path)


def test_almost_empty_text_counts_as_no_text_layer(make_pdf: MakePdf) -> None:
    # Scans often carry only a page number or a stamp as real text.
    path = make_pdf(["1", "2"])

    with pytest.raises(NoTextLayerError):
        extract_text(path)


def test_long_documents_are_truncated_and_stop_reading_early(make_pdf: MakePdf) -> None:
    page = "Lorem ipsum dolor sit amet. " * 20  # ~560 characters per page
    path = make_pdf([page] * 50)

    result = extract_text(path, max_chars=2000)

    assert len(result.text) == 2000
    assert result.truncated is True
    assert result.page_count == 50
    assert result.pages_read < 10  # did not parse the other 40+ pages


def test_corrupted_file_is_reported_as_unreadable(tmp_path: Path) -> None:
    path = tmp_path / "broken.pdf"
    path.write_bytes(b"%PDF-1.4\nthis is not really a pdf")

    with pytest.raises(UnreadablePdfError):
        extract_text(path)


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    # A missing file is a bug in the caller, not a bad upload: it must not be disguised.
    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "missing.pdf")
