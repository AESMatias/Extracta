"""Structured output the LLM must return for every processed PDF.

One root model, `DocumentSchema`, classifies the document and fills exactly one
type-specific section. The field descriptions are sent to the LLM as
instructions, so they are written for the model: they must work for documents
in any language.

Design notes:
- Sections are optional fields instead of a Python Union, because nullable
  fields are the JSON Schema shape both Gemini and OpenAI structured outputs
  support reliably.
- Amounts are plain numbers (no currency symbols, no thousands separators);
  the currency lives in its own ISO 4217 field.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Self

from pydantic import BaseModel, BeforeValidator, Field, model_validator

# Shared guidance repeated in descriptions so the LLM sees it next to each field.
_ANY_LANGUAGE = "Extract it regardless of the document's language; keep names as written."
_ISO_DATE = "Date in ISO 8601 format (YYYY-MM-DD). Null if absent."
_AMOUNT = "Plain number, no currency symbol or thousands separators. Null if absent."


def _normalize_code(value: Any) -> Any:
    # " usd " -> "USD": tolerate harmless formatting noise from the LLM.
    return value.strip().upper() if isinstance(value, str) else value


CurrencyCode = Annotated[
    str,
    BeforeValidator(_normalize_code),
    Field(
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 currency code, e.g. CLP, USD, EUR. Infer it from symbols or country.",
    ),
]


class DocumentType(StrEnum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    PURCHASE_ORDER = "purchase_order"
    QUOTE = "quote"
    BANK_STATEMENT = "bank_statement"
    CONTRACT = "contract"
    PAYSLIP = "payslip"
    RESUME = "resume"
    REPORT = "report"
    OTHER = "other"


# --------------------------------------------------------------------------
# Shared building blocks
# --------------------------------------------------------------------------


class Party(BaseModel):
    name: str = Field(description=f"Legal or trade name of the company or person. {_ANY_LANGUAGE}")
    tax_id: str | None = Field(
        default=None,
        description="Tax identifier exactly as printed (RUT, RFC, CUIT, NIF, VAT, EIN...).",
    )
    address: str | None = Field(default=None, description="Postal address as printed.")
    role: str | None = Field(
        default=None,
        description="Role in the document, e.g. 'client', 'provider', 'landlord', 'employer'.",
    )


class LineItem(BaseModel):
    description: str = Field(description=f"Product or service line. {_ANY_LANGUAGE}")
    quantity: float | None = Field(default=None, description="Units. Null if absent.")
    unit_price: float | None = Field(default=None, description=f"Price per unit. {_AMOUNT}")
    amount: float | None = Field(default=None, description=f"Line total. {_AMOUNT}")


# --------------------------------------------------------------------------
# Type-specific sections
# --------------------------------------------------------------------------


class CommercialDocumentData(BaseModel):
    """Invoices, receipts, purchase orders and quotes share this structure."""

    document_number: str | None = Field(default=None, description="Invoice, receipt, order or quote number as printed.")
    issue_date: date | None = Field(default=None, description=f"Issue date. {_ISO_DATE}")
    due_date: date | None = Field(default=None, description=f"Payment due date or quote expiry date. {_ISO_DATE}")
    issuer: Party = Field(description="Who issues the document: vendor, seller or provider.")
    recipient: Party | None = Field(default=None, description="Who receives it: customer or buyer. Null if absent.")
    currency: CurrencyCode | None = None
    subtotal: float | None = Field(default=None, description=f"Total before taxes. {_AMOUNT}")
    tax_amount: float | None = Field(default=None, description=f"Total taxes (VAT/IVA...). {_AMOUNT}")
    total_amount: float | None = Field(default=None, description=f"Final amount to pay, taxes included. {_AMOUNT}")
    line_items: list[LineItem] = Field(
        default_factory=list, description="Each product or service line, in document order."
    )


class BankStatementData(BaseModel):
    bank_name: str | None = Field(default=None, description="Issuing bank.")
    account_holder: str | None = Field(default=None, description="Account owner's name.")
    account_number_last4: str | None = Field(
        default=None,
        pattern=r"^\d{4}$",
        description="ONLY the last 4 digits of the account number, never the full number.",
    )
    currency: CurrencyCode | None = None
    period_start: date | None = Field(default=None, description=f"Statement start. {_ISO_DATE}")
    period_end: date | None = Field(default=None, description=f"Statement end. {_ISO_DATE}")
    opening_balance: float | None = Field(default=None, description=f"Balance at start. {_AMOUNT}")
    closing_balance: float | None = Field(default=None, description=f"Balance at end. {_AMOUNT}")
    total_credits: float | None = Field(default=None, description=f"Sum of deposits. {_AMOUNT}")
    total_debits: float | None = Field(default=None, description=f"Sum of withdrawals. {_AMOUNT}")


class ContractData(BaseModel):
    title: str | None = Field(default=None, description=f"Contract title. {_ANY_LANGUAGE}")
    parties: list[Party] = Field(default_factory=list, description="Every signing party, with its role.")
    effective_date: date | None = Field(default=None, description=f"Start date. {_ISO_DATE}")
    end_date: date | None = Field(default=None, description=f"Expiry date. {_ISO_DATE}")
    contract_value: float | None = Field(default=None, description=f"Total economic value, if stated. {_AMOUNT}")
    currency: CurrencyCode | None = None
    auto_renewal: bool | None = Field(default=None, description="True if it renews automatically. Null if not stated.")
    termination_notice_days: int | None = Field(
        default=None, description="Days of notice required to terminate. Null if not stated."
    )
    governing_law: str | None = Field(default=None, description="Jurisdiction or governing law, e.g. 'Chile'.")
    key_obligations: list[str] = Field(
        default_factory=list,
        description="Up to 5 main obligations, one short English sentence each.",
    )


class PayslipData(BaseModel):
    employer_name: str | None = Field(default=None, description="Employer company.")
    employee_name: str | None = Field(default=None, description="Employee full name.")
    period_start: date | None = Field(default=None, description=f"Pay period start. {_ISO_DATE}")
    period_end: date | None = Field(default=None, description=f"Pay period end. {_ISO_DATE}")
    pay_date: date | None = Field(default=None, description=f"Payment date. {_ISO_DATE}")
    currency: CurrencyCode | None = None
    gross_pay: float | None = Field(default=None, description=f"Pay before deductions. {_AMOUNT}")
    total_deductions: float | None = Field(
        default=None, description=f"Taxes, pension, health and other deductions. {_AMOUNT}"
    )
    net_pay: float | None = Field(default=None, description=f"Amount actually paid. {_AMOUNT}")


class ResumeData(BaseModel):
    full_name: str | None = Field(default=None, description="Candidate full name.")
    email: str | None = Field(default=None, description="Contact email.")
    phone: str | None = Field(default=None, description="Contact phone as printed.")
    location: str | None = Field(default=None, description="City and/or country.")
    current_title: str | None = Field(default=None, description="Most recent job title.")
    years_of_experience: float | None = Field(
        default=None, description="Total professional years, estimated from the work history."
    )
    skills: list[str] = Field(default_factory=list, description="Technical and soft skills.")
    languages: list[str] = Field(default_factory=list, description="Spoken languages.")
    education: list[str] = Field(default_factory=list, description="Degrees, each as 'Degree - Institution - Year'.")


class ReportData(BaseModel):
    title: str | None = Field(default=None, description=f"Report title. {_ANY_LANGUAGE}")
    author: str | None = Field(default=None, description="Author person or organization.")
    report_date: date | None = Field(default=None, description=f"Publication date. {_ISO_DATE}")
    period_covered: str | None = Field(default=None, description="Period analyzed, as written, e.g. 'Q3 2026'.")
    key_findings: list[str] = Field(
        default_factory=list,
        description="Up to 5 main findings or conclusions, one short English sentence each.",
    )


# Which section holds the data of each document type ("other" has none).
SECTION_BY_TYPE: dict[DocumentType, str] = {
    DocumentType.INVOICE: "commercial",
    DocumentType.RECEIPT: "commercial",
    DocumentType.PURCHASE_ORDER: "commercial",
    DocumentType.QUOTE: "commercial",
    DocumentType.BANK_STATEMENT: "bank_statement",
    DocumentType.CONTRACT: "contract",
    DocumentType.PAYSLIP: "payslip",
    DocumentType.RESUME: "resume",
    DocumentType.REPORT: "report",
}


# --------------------------------------------------------------------------
# Root model
# --------------------------------------------------------------------------


class DocumentSchema(BaseModel):
    document_type: DocumentType = Field(
        description=(
            "Classify the document. invoice: bill requesting payment (includes utility bills). "
            "receipt: proof of a payment already made (ticket, boleta). "
            "purchase_order: buyer's order to a supplier. quote: price offer or estimate. "
            "bank_statement: account movements over a period. contract: agreement between "
            "parties. payslip: salary statement (liquidación de sueldo). resume: CV. "
            "report: analytical or periodic report (informe). other: none of the above."
        )
    )
    language: str | None = Field(
        default=None, description="Main language of the document, ISO 639-1 code (es, en, pt...)."
    )
    title: str | None = Field(default=None, description="The document's own title or heading, as written.")
    summary: str = Field(description="Two or three sentences in English describing what the document is about.")
    commercial: CommercialDocumentData | None = Field(
        default=None, description="Fill ONLY for invoice, receipt, purchase_order or quote."
    )
    bank_statement: BankStatementData | None = Field(default=None, description="Fill ONLY for bank_statement.")
    contract: ContractData | None = Field(default=None, description="Fill ONLY for contract.")
    payslip: PayslipData | None = Field(default=None, description="Fill ONLY for payslip.")
    resume: ResumeData | None = Field(default=None, description="Fill ONLY for resume.")
    report: ReportData | None = Field(default=None, description="Fill ONLY for report.")

    @model_validator(mode="after")
    def keep_only_the_matching_section(self) -> Self:
        expected = SECTION_BY_TYPE.get(self.document_type)
        if expected is not None and getattr(self, expected) is None:
            raise ValueError(f"document_type={self.document_type} requires the '{expected}' section")
        # Drop sections the LLM filled for other types, so stored data stays consistent.
        for name in set(SECTION_BY_TYPE.values()) - {expected}:
            setattr(self, name, None)
        return self

    @property
    def section(self) -> BaseModel | None:
        """The type-specific data of this document, or None for 'other'."""
        name = SECTION_BY_TYPE.get(self.document_type)
        return getattr(self, name) if name else None
