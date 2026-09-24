from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas import (
    SECTION_BY_TYPE,
    BankStatementData,
    CommercialDocumentData,
    DocumentSchema,
    DocumentType,
)


def invoice_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "document_type": "invoice",
        "language": "es",
        "title": "Factura electrónica N° 1234",
        "summary": "Invoice from Acme SpA to Beta Ltda for consulting services.",
        "commercial": {
            "document_number": "1234",
            "issue_date": "2026-09-01",
            "due_date": "2026-09-30",
            "issuer": {"name": "Acme SpA", "tax_id": "76.123.456-7"},
            "recipient": {"name": "Beta Ltda"},
            "currency": "CLP",
            "subtotal": 100000,
            "tax_amount": 19000,
            "total_amount": 119000,
            "line_items": [
                {"description": "Consulting", "quantity": 10, "unit_price": 10000, "amount": 100000}
            ],
        },
    }
    payload.update(overrides)
    return payload


def test_valid_invoice_is_parsed() -> None:
    doc = DocumentSchema.model_validate(invoice_payload())

    assert doc.document_type is DocumentType.INVOICE
    assert isinstance(doc.section, CommercialDocumentData)
    assert doc.commercial is not None
    assert doc.commercial.issuer.name == "Acme SpA"
    assert doc.commercial.total_amount == 119000
    assert doc.commercial.issue_date is not None
    assert doc.commercial.issue_date.isoformat() == "2026-09-01"


def test_optional_commercial_fields_can_be_missing() -> None:
    # Only the issuer name is mandatory: a receipt often has no number or recipient.
    doc = DocumentSchema.model_validate(
        {
            "document_type": "receipt",
            "summary": "Supermarket receipt.",
            "commercial": {"issuer": {"name": "Supermercado Lider"}},
        }
    )

    assert doc.commercial is not None
    assert doc.commercial.document_number is None
    assert doc.commercial.total_amount is None
    assert doc.commercial.line_items == []


def test_issuer_name_is_required() -> None:
    payload = invoice_payload()
    del payload["commercial"]["issuer"]["name"]

    with pytest.raises(ValidationError, match="name"):
        DocumentSchema.model_validate(payload)


def test_matching_section_is_required() -> None:
    with pytest.raises(ValidationError, match="commercial"):
        DocumentSchema.model_validate(invoice_payload(commercial=None))


def test_sections_of_other_types_are_discarded() -> None:
    doc = DocumentSchema.model_validate(
        invoice_payload(bank_statement={"bank_name": "Banco Estado"})
    )

    assert doc.bank_statement is None
    assert doc.commercial is not None


def test_other_type_needs_no_section() -> None:
    doc = DocumentSchema.model_validate({"document_type": "other", "summary": "A restaurant menu."})

    assert doc.section is None


def test_unknown_document_type_is_rejected() -> None:
    with pytest.raises(ValidationError, match="document_type"):
        DocumentSchema.model_validate(invoice_payload(document_type="spaceship_manual"))


def test_non_numeric_amount_is_rejected() -> None:
    payload = invoice_payload()
    payload["commercial"]["total_amount"] = "one hundred"

    with pytest.raises(ValidationError, match="total_amount"):
        DocumentSchema.model_validate(payload)


def test_currency_is_normalized_to_upper_case() -> None:
    payload = invoice_payload()
    payload["commercial"]["currency"] = " usd "

    doc = DocumentSchema.model_validate(payload)

    assert doc.commercial is not None
    assert doc.commercial.currency == "USD"


def test_invalid_currency_code_is_rejected() -> None:
    payload = invoice_payload()
    payload["commercial"]["currency"] = "dollars"

    with pytest.raises(ValidationError, match="currency"):
        DocumentSchema.model_validate(payload)


@pytest.mark.parametrize("value", ["123", "12345", "12a4"])
def test_account_last4_must_be_exactly_four_digits(value: str) -> None:
    with pytest.raises(ValidationError, match="account_number_last4"):
        BankStatementData.model_validate({"account_number_last4": value})


@pytest.mark.parametrize(
    ("document_type", "section", "data"),
    [
        (
            "bank_statement",
            "bank_statement",
            {"bank_name": "Banco de Chile", "closing_balance": -50.5},
        ),
        ("contract", "contract", {"title": "Service agreement", "auto_renewal": True}),
        ("payslip", "payslip", {"employer_name": "Acme SpA", "net_pay": 850000}),
        ("resume", "resume", {"full_name": "Ana Pérez", "skills": ["Python", "SQL"]}),
        ("report", "report", {"title": "Q3 results", "key_findings": ["Revenue +12%"]}),
    ],
)
def test_each_document_type_fills_its_own_section(
    document_type: str, section: str, data: dict[str, Any]
) -> None:
    doc = DocumentSchema.model_validate(
        {"document_type": document_type, "summary": "Test document.", section: data}
    )

    assert doc.section is getattr(doc, section)


def test_every_type_except_other_has_a_section() -> None:
    assert set(SECTION_BY_TYPE) == set(DocumentType) - {DocumentType.OTHER}


def test_json_schema_carries_descriptions_for_the_llm() -> None:
    schema = DocumentSchema.model_json_schema()

    assert "document_type" in schema["required"]
    assert schema["properties"]["summary"]["description"]
    assert schema["$defs"]["CommercialDocumentData"]["properties"]["total_amount"]["description"]
