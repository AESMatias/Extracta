"""Real calls to the configured LLM provider (costs a fraction of a cent per run).

docker run --rm --env-file .env -v "$PWD":/src -w /src pdf-process-pipeline:dev pytest -m integration
"""

import os

import pytest

from app.config import Settings
from app.llm import DocumentExtractor, build_extractor
from app.schemas import DocumentType

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")), reason="needs an LLM API key"
    ),
]

INVOICE = """--- Page 1 ---
FACTURA ELECTRÓNICA N° 004512
Acme Servicios SpA — RUT 76.123.456-7 — Av. Providencia 1234, Santiago
Fecha de emisión: 15/08/2026   Vencimiento: 14/09/2026
Señor(es): Beta Ltda — RUT 77.987.654-3
Detalle                      Cant.  Precio unit.   Total
Consultoría de datos           10     $10.000     $100.000
Neto: $100.000   IVA 19%: $19.000   TOTAL: $119.000"""

CONTRACT = """--- Page 1 ---
SERVICE AGREEMENT
This Service Agreement is entered into on March 1, 2026 between Northwind Traders Inc.
("Client") and Contoso Consulting LLC ("Provider"). The Provider will deliver monthly data
analysis reports. Term: twelve (12) months from the effective date, renewing automatically
for successive one-year periods unless either party gives sixty (60) days written notice.
Fees: USD 24,000 per year. This Agreement is governed by the laws of the State of New York."""

BANK_STATEMENT = """--- Page 1 ---
BANCO DEL SUR — ESTADO DE CUENTA
Titular: Ana Pérez Soto   Cuenta corriente N° 0012345678904321
Período: 01/07/2026 al 31/07/2026   Moneda: CLP
Saldo inicial: 1.250.000   Total abonos: 2.100.000   Total cargos: 1.830.500
Saldo final: 1.519.500"""


@pytest.fixture(scope="module")
def extractor() -> DocumentExtractor:
    return build_extractor(Settings())


def test_real_invoice_in_spanish(extractor: DocumentExtractor) -> None:
    doc = extractor.extract(INVOICE)

    assert doc.document_type is DocumentType.INVOICE
    assert doc.commercial is not None
    assert "Acme" in doc.commercial.issuer.name
    assert doc.commercial.document_number is not None and "4512" in doc.commercial.document_number
    assert doc.commercial.currency == "CLP"
    assert doc.commercial.total_amount == 119000
    assert doc.commercial.tax_amount == 19000
    assert doc.commercial.issue_date is not None and doc.commercial.issue_date.isoformat() == "2026-08-15"


def test_real_contract_in_english(extractor: DocumentExtractor) -> None:
    doc = extractor.extract(CONTRACT)

    assert doc.document_type is DocumentType.CONTRACT
    assert doc.contract is not None
    assert len(doc.contract.parties) == 2
    assert doc.contract.auto_renewal is True
    assert doc.contract.termination_notice_days == 60
    assert doc.contract.currency == "USD"


def test_real_bank_statement_keeps_only_the_last_four_digits(extractor: DocumentExtractor) -> None:
    doc = extractor.extract(BANK_STATEMENT)

    assert doc.document_type is DocumentType.BANK_STATEMENT
    assert doc.bank_statement is not None
    assert doc.bank_statement.account_number_last4 == "4321"
    assert doc.bank_statement.closing_balance == 1519500
    assert "0012345678904321" not in doc.model_dump_json()  # the full account number never leaks
