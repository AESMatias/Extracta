import json
import uuid

from app.models import Document
from app.schemas import DocumentSchema


def test_from_extraction_maps_the_schema_to_a_row() -> None:
    task_id = uuid.uuid4()
    extraction = DocumentSchema.model_validate(
        {
            "document_type": "invoice",
            "language": "es",
            "title": "Factura 1234",
            "summary": "Invoice from Acme SpA.",
            "commercial": {"issuer": {"name": "Acme SpA"}, "issue_date": "2026-09-01", "total_amount": 119000},
        }
    )

    row = Document.from_extraction(
        task_id=task_id,
        filename="factura.pdf",
        extraction=extraction,
        llm_provider="gemini",
        llm_model="gemini-3.1-flash-lite",
    )

    assert row.id == task_id
    assert row.filename == "factura.pdf"
    assert row.document_type == "invoice"
    assert row.language == "es"
    assert row.title == "Factura 1234"
    assert row.summary == "Invoice from Acme SpA."
    assert row.llm_provider == "gemini"
    assert row.llm_model == "gemini-3.1-flash-lite"
    # Stored as JSON: dates become ISO strings, the whole payload must serialize.
    assert row.data["commercial"]["issue_date"] == "2026-09-01"
    assert json.loads(json.dumps(row.data)) == row.data


def test_documents_table_definition() -> None:
    table = Document.metadata.tables["documents"]

    assert table.name == "documents"
    assert {c.name for c in table.primary_key.columns} == {"id"}
    assert table.c.summary.nullable is False
    assert table.c.data.nullable is False
    assert {i.name for i in table.indexes} >= {"ix_documents_document_type", "ix_documents_created_at"}
