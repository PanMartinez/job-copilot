import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel

# Provisional dimension pending the embedding model chosen in the RAG step.
EMBEDDING_DIM = 1536


class DocumentType(enum.StrEnum):
    CV = "cv"
    INTERVIEW_FEEDBACK = "interview_feedback"
    COMPANY_RESEARCH = "company_research"
    COVER_LETTER = "cover_letter"


class Document(BaseModel):
    __tablename__ = "documents"

    type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type", values_callable=lambda enum_cls: [e.value for e in enum_cls])
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    doc_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
