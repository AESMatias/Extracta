import csv
import inspect
import io
import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.export import (
    MAX_EXPORT_ITEMS,
    ExportItem,
    UnifiedExportRequest,
    individual_csv,
    individual_json,
    individual_xlsx,
    unified_columns,
    unified_csv,
    unified_json,
    unified_xlsx,
)
from app.schemas import DocumentSchema

BOM = "\ufeff"


def doc(data: dict[str, Any]) -> DocumentSchema:
    return DocumentSchema.model_validate(data)


INVOICE = doc(
    {
        "document_type": "invoice",
        "language": "es",
        "title": "Factura electrónica N° 4512",
        "summary": "Invoice from Acme to Beta.",
        "commercial": {
            "document_number": "004512",
            "issue_date": "2026-08-15",
            "issuer": {"name": "Acme Servicios SpA", "tax_id": "76.123.456-7"},
            "recipient": {"name": "Beta Ltda"},
            "currency": "CLP",
            "subtotal": 100000,
            "tax_amount": 19000,
            "total_amount": 119000.0,
            "line_items": [
                {"description": "Consultoría", "quantity": 10, "unit_price": 10000, "amount": 100000},
                {"description": "Soporte", "quantity": 0.5, "unit_price": 19000, "amount": 9500},
            ],
        },
    }
)
BANK = doc(
    {
        "document_type": "bank_statement",
        "summary": "Statement.",
        "bank_statement": {"bank_name": "Banco del Sur", "account_number_last4": "4321", "closing_balance": -50.5},
    }
)
CONTRACT = doc(
    {
        "document_type": "contract",
        "summary": "Service agreement.",
        "contract": {
            "title": "Service agreement",
            "parties": [{"name": "Northwind", "role": "client"}, {"name": "Contoso", "role": "provider"}],
            "auto_renewal": True,
            "key_obligations": ["Deliver monthly reports", "Pay within 30 days"],
        },
    }
)
OTHER = doc({"document_type": "other", "summary": "A restaurant menu."})


def read(chunks: Any) -> list[dict[str, str]]:
    text = "".join(chunks)
    assert text.startswith(BOM)  # Excel needs the BOM to show accents correctly
    return list(csv.DictReader(io.StringIO(text.removeprefix(BOM))))


# --------------------------------------------------------------------------- individual


def test_individual_invoice_has_one_row_per_line_item() -> None:
    rows = read(individual_csv(INVOICE, filename="factura.pdf"))

    assert len(rows) == 2
    first, second = rows
    assert first["filename"] == "factura.pdf"
    assert first["document_type"] == "invoice"
    assert first["issuer.name"] == "Acme Servicios SpA"
    assert first["total_amount"] == "119000"  # 119000.0 written as a clean number
    assert first["issue_date"] == "2026-08-15"
    assert first["line_item.description"] == "Consultoría"
    assert second["line_item.quantity"] == "0.5"
    assert second["issuer.name"] == "Acme Servicios SpA"  # document columns repeated on every item row
    assert "line_items" not in first  # replaced by the line_item.* columns


def test_individual_invoice_without_line_items_still_has_one_row() -> None:
    no_items = INVOICE.model_copy(update={"commercial": INVOICE.commercial.model_copy(update={"line_items": []})})  # type: ignore[union-attr]

    rows = read(individual_csv(no_items, filename=None))

    assert len(rows) == 1
    assert rows[0]["line_item.description"] == ""
    assert rows[0]["filename"] == ""


def test_individual_contract_flattens_lists() -> None:
    [row] = read(individual_csv(CONTRACT, filename="contrato.pdf"))

    assert row["parties"] == "Northwind | client; Contoso | provider"
    assert row["key_obligations"] == "Deliver monthly reports; Pay within 30 days"
    assert row["auto_renewal"] == "true"
    assert "commercial.issuer.name" not in row  # only the columns of its own section


def test_individual_other_has_only_the_common_columns() -> None:
    [row] = read(individual_csv(OTHER, filename="menu.pdf"))

    assert list(row) == ["filename", "document_type", "language", "title", "summary"]


# --------------------------------------------------------------------------- unified


def test_unified_has_one_row_per_document_and_stable_columns() -> None:
    items = [ExportItem(filename="a.pdf", document=INVOICE), ExportItem(filename="b.pdf", document=BANK)]

    text = "".join(unified_csv(items))
    header = next(csv.reader(io.StringIO(text.removeprefix(BOM))))
    rows = read([text])

    assert header == unified_columns()  # derived from the schema, not from the data
    assert len(rows) == 2
    assert rows[0]["commercial.total_amount"] == "119000"
    assert rows[0]["commercial.line_items"] == "2 items"
    assert rows[0]["bank_statement.bank_name"] == ""
    assert rows[1]["bank_statement.account_number_last4"] == "4321"
    assert rows[1]["commercial.total_amount"] == ""


def test_unified_columns_are_the_same_for_any_batch() -> None:
    only_other = read(unified_csv([ExportItem(filename="x.pdf", document=OTHER)]))

    assert list(only_other[0]) == unified_columns()
    assert "report.key_findings" in unified_columns()


def test_exports_are_streamed_not_built_in_memory() -> None:
    assert inspect.isgenerator(individual_csv(INVOICE, filename="a.pdf"))
    assert inspect.isgenerator(unified_csv([ExportItem(filename="a.pdf", document=INVOICE)]))


# --------------------------------------------------------------------------- formula injection


@pytest.mark.parametrize("payload", ['=HYPERLINK("http://evil")', "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"])
def test_text_that_looks_like_a_formula_is_escaped(payload: str) -> None:
    evil = doc({"document_type": "other", "summary": payload})

    [row] = read(individual_csv(evil, filename=payload))

    assert row["summary"] == "'" + payload
    assert row["filename"] == "'" + payload


def test_negative_numbers_stay_numeric() -> None:
    rows = read(unified_csv([ExportItem(filename="b.pdf", document=BANK)]))

    assert rows[0]["bank_statement.closing_balance"] == "-50.5"  # a number, not a formula


# --------------------------------------------------------------------------- request validation


def test_request_payload_is_validated_against_the_schema() -> None:
    bad = {"items": [{"filename": "a.pdf", "document": {"document_type": "invoice", "summary": "no section"}}]}

    with pytest.raises(ValidationError):
        UnifiedExportRequest.model_validate(bad)


def test_request_needs_at_least_one_item() -> None:
    with pytest.raises(ValidationError):
        UnifiedExportRequest.model_validate({"items": []})


def test_request_is_capped() -> None:
    item = {"filename": "a.pdf", "document": {"document_type": "other", "summary": "x"}}

    with pytest.raises(ValidationError):
        UnifiedExportRequest.model_validate({"items": [item] * (MAX_EXPORT_ITEMS + 1)})


# --------------------------------------------------------------------------- XLSX


def workbook(data: bytes) -> Any:
    from openpyxl import load_workbook

    return load_workbook(io.BytesIO(data))


def test_individual_xlsx_keeps_numbers_dates_and_leading_zeros() -> None:
    sheet = workbook(individual_xlsx(INVOICE, filename="factura.pdf")).active

    header = [cell.value for cell in sheet[1]]
    first = dict(zip(header, [cell.value for cell in sheet[2]], strict=True))
    assert sheet.max_row == 3  # header + 2 line items
    assert first["total_amount"] == 119000  # a real number: Excel can sum it
    assert first["issue_date"].date().isoformat() == "2026-08-15"  # a real date
    assert first["document_number"] == "004512"  # text: leading zeros survive (unlike CSV)
    assert first["line_item.description"] == "Consultoría"
    assert sheet.freeze_panes == "A2"  # header stays visible while scrolling
    assert sheet.auto_filter.ref is not None  # filter buttons on the header


def test_xlsx_stores_formula_like_text_as_plain_text() -> None:
    evil = doc({"document_type": "other", "summary": '=HYPERLINK("http://evil")'})

    sheet = workbook(individual_xlsx(evil, filename="a.pdf")).active

    cell = sheet.cell(row=2, column=5)  # summary
    assert cell.value == '=HYPERLINK("http://evil")'  # exact text, no quote prefix needed
    assert cell.data_type == "s"  # a string cell, never a formula


def test_unified_xlsx_has_the_same_columns_as_the_csv() -> None:
    items = [ExportItem(filename="a.pdf", document=INVOICE), ExportItem(filename="b.pdf", document=BANK)]

    sheet = workbook(unified_xlsx(items)).active

    assert [cell.value for cell in sheet[1]] == unified_columns()
    assert sheet.max_row == 3
    assert sheet.cell(row=3, column=unified_columns().index("bank_statement.closing_balance") + 1).value == -50.5


# --------------------------------------------------------------------------- JSON


def test_individual_json_round_trips_to_the_schema() -> None:
    data = json.loads(individual_json(ExportItem(filename="factura.pdf", document=INVOICE)))

    assert data["filename"] == "factura.pdf"
    assert DocumentSchema.model_validate(data["document"]) == INVOICE
    assert "Consultoría" in individual_json(ExportItem(filename="a.pdf", document=INVOICE)).decode()  # not \\u00ed


def test_unified_json_lists_every_document() -> None:
    items = [ExportItem(filename="a.pdf", document=INVOICE), ExportItem(filename="b.pdf", document=BANK)]

    data = json.loads(unified_json(items))

    assert data["count"] == 2
    assert [item["filename"] for item in data["items"]] == ["a.pdf", "b.pdf"]
    assert "exported_at" in data
