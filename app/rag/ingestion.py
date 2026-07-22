from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

import app.rag.embeddings as embeddings
from app.models.document import Document, DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingProvider


async def ingest_document(
    db: AsyncSession,
    document_id: int,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> int:
    """(Re)compute chunks and embeddings for one document. Returns the chunk count.

    Existing chunks for the document are deleted and recreated from scratch -
    simpler than diffing, and cheap at personal-corpus scale.
    """
    provider = embedding_provider or embeddings.get_embedding_provider()

    document = await db.get(Document, document_id)
    if document is None:
        return 0

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

    chunks = chunk_text(document.content)
    if not chunks:
        await db.commit()
        return 0

    vectors = await provider.embed_texts([chunk.content for chunk in chunks])
    for chunk, vector in zip(chunks, vectors, strict=True):
        db.add(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=vector,
            )
        )
    await db.commit()
    return len(chunks)
