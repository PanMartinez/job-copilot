import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentType
from app.rag.embeddings import EmbeddingProvider
from app.services import retrieval_service

pytestmark = pytest.mark.asyncio

_DIM = 1536


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Always returns the same fixed query vector - content embeddings in these
    tests are hand-built and inserted directly, so only the query needs faking."""

    def __init__(self, query_vector: list[float]) -> None:
        self._query_vector = query_vector

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._query_vector for _ in texts]


def _basis_vector(index: int) -> list[float]:
    vector = [0.0] * _DIM
    vector[index] = 1.0
    return vector


def _near_vector(index: int, noise_index: int, noise: float = 0.1) -> list[float]:
    vector = _basis_vector(index)
    vector[noise_index] = noise
    norm = sum(x * x for x in vector) ** 0.5
    return [x / norm for x in vector]


QUERY_VECTOR = _basis_vector(0)


async def _add_document(db: AsyncSession, title: str) -> Document:
    document = Document(type=DocumentType.CV, title=title, content="placeholder")
    db.add(document)
    await db.commit()
    return document


async def _add_chunk(
    db: AsyncSession, document: Document, *, index: int, content: str, embedding: list[float]
) -> DocumentChunk:
    chunk = DocumentChunk(document_id=document.id, chunk_index=index, content=content, embedding=embedding)
    db.add(chunk)
    await db.commit()
    return chunk


async def test_semantic_only_match_surfaces(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Backend CV")
    await _add_chunk(
        db_session,
        document,
        index=0,
        content="Experienced with container orchestration and service scaling.",
        embedding=_near_vector(0, noise_index=1),
    )

    results = await retrieval_service.hybrid_search(
        db_session, "kubernetes", embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )

    assert len(results) == 1
    assert results[0].vector_rank == 1
    assert results[0].text_rank is None


async def test_text_only_match_surfaces(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Widget Co Research")
    text_only = await _add_chunk(
        db_session,
        document,
        index=0,
        content="We run everything on kubernetes across three regions.",
        embedding=_basis_vector(5),  # far from the query vector
    )
    filler = await _add_chunk(
        db_session,
        document,
        index=1,
        content="General notes about our office culture.",
        embedding=_basis_vector(0),  # exact match to the query vector
    )

    results = await retrieval_service.hybrid_search(
        db_session,
        "kubernetes",
        vector_candidates=1,  # forces the vector leg to pick only the closest chunk
        embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR),
    )

    by_id = {r.chunk_id: r for r in results}
    assert by_id[text_only.id].text_rank == 1
    assert by_id[text_only.id].vector_rank is None
    assert by_id[filler.id].vector_rank == 1
    assert by_id[filler.id].text_rank is None


async def test_dual_signal_chunk_outranks_single_signal(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Backend CV")
    both = await _add_chunk(
        db_session,
        document,
        index=0,
        content="Led our kubernetes migration end to end.",
        embedding=_basis_vector(0),
    )
    semantic_only = await _add_chunk(
        db_session,
        document,
        index=1,
        content="Comfortable with container orchestration generally.",
        embedding=_near_vector(0, noise_index=1),
    )
    text_only = await _add_chunk(
        db_session,
        document,
        index=2,
        content="Our kubernetes cluster runs in three regions.",
        embedding=_basis_vector(7),
    )

    results = await retrieval_service.hybrid_search(
        db_session, "kubernetes", embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )

    ids_in_order = [r.chunk_id for r in results]
    assert ids_in_order == [both.id, text_only.id, semantic_only.id]


async def test_max_chunks_is_respected(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Backend CV")
    for i in range(5):
        await _add_chunk(
            db_session,
            document,
            index=i,
            content=f"Kubernetes note number {i}.",
            embedding=_basis_vector(0),
        )

    results = await retrieval_service.hybrid_search(
        db_session, "kubernetes", max_chunks=2, embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )

    assert len(results) == 2


async def test_document_metadata_is_populated(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Backend CV")
    await _add_chunk(
        db_session,
        document,
        index=0,
        content="Kubernetes deployment experience.",
        embedding=_basis_vector(0),
    )

    [result] = await retrieval_service.hybrid_search(
        db_session, "kubernetes", embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )

    assert result.document_id == document.id
    assert result.document_title == "Backend CV"
    assert result.document_type == "cv"


async def test_blank_query_returns_no_results(db_session: AsyncSession) -> None:
    results = await retrieval_service.hybrid_search(
        db_session, "   ", embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )
    assert results == []


async def test_multi_word_query_still_matches_single_shared_lexeme(db_session: AsyncSession) -> None:
    """Regression test: websearch_to_tsquery's implicit AND would zero out the
    text arm whenever any one of several query words is absent from the chunk.
    A query with one lexeme actually present in the chunk (the rest are not)
    must still surface that chunk via the text arm."""
    document = await _add_document(db_session, "Backend CV")
    chunk = await _add_chunk(
        db_session,
        document,
        index=0,
        content="Led our kubernetes migration end to end.",
        embedding=_basis_vector(5),  # far from the query vector - text arm only
    )

    results = await retrieval_service.hybrid_search(
        db_session,
        "checkout card payment retail kubernetes shops",
        embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR),
    )

    by_id = {r.chunk_id: r for r in results}
    assert chunk.id in by_id
    assert by_id[chunk.id].text_rank == 1


async def test_dual_arm_match_score_exceeds_single_arm_top_rank(db_session: AsyncSession) -> None:
    document = await _add_document(db_session, "Backend CV")
    both = await _add_chunk(
        db_session,
        document,
        index=0,
        content="Led our kubernetes migration end to end.",
        embedding=_basis_vector(0),
    )

    [result] = await retrieval_service.hybrid_search(
        db_session, "kubernetes", embedding_provider=_FakeEmbeddingProvider(QUERY_VECTOR)
    )

    assert result.chunk_id == both.id
    assert result.vector_rank == 1
    assert result.text_rank == 1
    assert result.rrf_score > 1.0 / (retrieval_service.RRF_K + 1)
