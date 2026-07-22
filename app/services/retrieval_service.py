"""
Hybrid retrieval: pgvector cosine similarity + Postgres full-text search,
merged with Reciprocal Rank Fusion (RRF).

Why hybrid rather than either alone: cosine similarity over embeddings catches
paraphrases and semantically related passages that share no vocabulary with
the query, but can miss an exact keyword/name/acronym match that carries low
semantic salience (e.g. a specific company or tool name). Full-text search is
the mirror image - great at exact terms, blind to paraphrase. RRF merges the
two ranked lists using only rank position (not the two incompatible raw score
scales), so neither signal needs to be recalibrated against the other.
"""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import Row, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import app.rag.embeddings as embeddings
from app.models.document import Document, DocumentChunk
from app.rag.embeddings import EmbeddingProvider

# Standard RRF constant from Cormack, Clarke & Buettcher (2009),
# "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods".
RRF_K = 60

_TEXT_SEARCH_SQL = text(
    """
    WITH q AS (
        SELECT to_tsquery(
            'english',
            array_to_string(tsvector_to_array(to_tsvector('english', :query)), ' | ')
        ) AS tsq
    )
    SELECT dc.id AS chunk_id, dc.document_id, dc.content,
           d.title AS document_title, d.type AS document_type,
           ts_rank(dc.content_tsv, q.tsq) AS score
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    CROSS JOIN q
    WHERE dc.content_tsv @@ q.tsq
    ORDER BY score DESC
    LIMIT :limit
    """
)


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    document_type: str
    content: str
    rrf_score: float
    vector_rank: int | None = None
    text_rank: int | None = None


async def hybrid_search(
    db: AsyncSession,
    query: str,
    *,
    max_chunks: int = 8,
    vector_candidates: int = 30,
    text_candidates: int = 30,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[RetrievedChunk]:
    if not query or not query.strip():
        return []

    provider = embedding_provider or embeddings.get_embedding_provider()
    [query_vector] = await provider.embed_texts([query])

    vector_rows = await _vector_search(db, query_vector, limit=vector_candidates)
    text_rows = await _text_search(db, query, limit=text_candidates)
    return _reciprocal_rank_fusion(vector_rows, text_rows, max_chunks=max_chunks)


async def _vector_search(db: AsyncSession, query_vector: list[float], *, limit: int) -> list[Row]:
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.document_id,
            DocumentChunk.content,
            Document.title.label("document_title"),
            Document.type.label("document_type"),
            distance.label("distance"),
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.all())


async def _text_search(db: AsyncSession, query: str, *, limit: int) -> list[Row]:
    result = await db.execute(_TEXT_SEARCH_SQL, {"query": query, "limit": limit})
    return list(result.all())


def _reciprocal_rank_fusion(
    vector_rows: list[Row], text_rows: list[Row], *, max_chunks: int
) -> list[RetrievedChunk]:
    scores: dict[int, float] = defaultdict(float)
    vector_ranks: dict[int, int] = {}
    text_ranks: dict[int, int] = {}
    rows_by_id: dict[int, Row] = {}

    for rank, row in enumerate(vector_rows, start=1):
        scores[row.chunk_id] += 1.0 / (RRF_K + rank)
        vector_ranks[row.chunk_id] = rank
        rows_by_id.setdefault(row.chunk_id, row)

    for rank, row in enumerate(text_rows, start=1):
        scores[row.chunk_id] += 1.0 / (RRF_K + rank)
        text_ranks[row.chunk_id] = rank
        rows_by_id.setdefault(row.chunk_id, row)

    ranked_ids = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)[:max_chunks]

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=rows_by_id[chunk_id].document_id,
            document_title=rows_by_id[chunk_id].document_title,
            document_type=rows_by_id[chunk_id].document_type,
            content=rows_by_id[chunk_id].content,
            rrf_score=scores[chunk_id],
            vector_rank=vector_ranks.get(chunk_id),
            text_rank=text_ranks.get(chunk_id),
        )
        for chunk_id in ranked_ids
    ]
