import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentType
from app.rag.embeddings import EmbeddingProvider
from app.rag.ingestion import ingest_document

pytestmark = pytest.mark.asyncio


class _FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(i)] + [0.0] * 1535 for i in range(len(texts))]


async def _add_document(db: AsyncSession, content: str) -> Document:
    document = Document(type=DocumentType.CV, title="My CV", content=content)
    db.add(document)
    await db.commit()
    return document


async def _chunks_for(db: AsyncSession, document_id: int) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


async def test_ingest_document_creates_chunks_with_embeddings(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Experienced backend engineer. " * 20)
    provider = _FakeEmbeddingProvider()

    count = await ingest_document(db_session, document.id, embedding_provider=provider)

    assert count > 0
    chunks = await _chunks_for(db_session, document.id)
    assert len(chunks) == count
    assert all(c.embedding is not None for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(count))
    assert provider.calls  # embed_texts was actually called


async def test_ingest_document_replaces_existing_chunks(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Short CV content.")
    provider = _FakeEmbeddingProvider()

    first_count = await ingest_document(db_session, document.id, embedding_provider=provider)
    second_count = await ingest_document(db_session, document.id, embedding_provider=provider)

    chunks = await _chunks_for(db_session, document.id)
    assert second_count == first_count
    assert len(chunks) == second_count  # re-ingesting doesn't duplicate rows


async def test_ingest_document_missing_document_returns_zero(db_session: AsyncSession) -> None:
    provider = _FakeEmbeddingProvider()

    count = await ingest_document(db_session, 999999, embedding_provider=provider)

    assert count == 0
    assert provider.calls == []
