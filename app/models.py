"""Database tables.

`documents` stores the results of persistent-mode tasks only. Task status
(pending, processing, failed...) lives in Celery's Redis result backend for
both modes, so this table only ever holds completed extractions.
"""

import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.schemas import DocumentSchema


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # same UUID as the Celery task
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str | None] = mapped_column(String(8))
    title: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)  # full DocumentSchema as JSON
    llm_provider: Mapped[str] = mapped_column(String(32))
    llm_model: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    @classmethod
    def from_extraction(
        cls,
        *,
        task_id: uuid.UUID,
        filename: str,
        extraction: DocumentSchema,
        llm_provider: str,
        llm_model: str,
    ) -> Self:
        return cls(
            id=task_id,
            filename=filename,
            document_type=extraction.document_type.value,
            language=extraction.language,
            title=extraction.title,
            summary=extraction.summary,
            data=extraction.model_dump(mode="json"),  # mode="json": dates become "YYYY-MM-DD" strings
            llm_provider=llm_provider,
            llm_model=llm_model,
        )
