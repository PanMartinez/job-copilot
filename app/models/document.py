import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# Dimension of OpenAI's text-embedding-3-small, the default RAG embedding provider
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


class DocumentChunk(BaseModel):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_chunk"),
        Index("ix_document_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
    )

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    content_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', content)", persisted=True), nullable=True
    )

    document: Mapped[Document] = relationship("Document", backref="chunks")
