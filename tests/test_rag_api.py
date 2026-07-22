import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk

pytestmark = pytest.mark.asyncio


async def _create_document(client: AsyncClient, *, content: str) -> dict:
    response = await client.post(
        "/api/v1/documents",
        json={"type": "cv", "title": "My CV", "content": content},
    )
    assert response.status_code == 201
    return response.json()


async def _insert_chunk_for(db_session: AsyncSession, document_id: int, content: str) -> None:
    # The autouse _stub_ingestion_delay fixture prevents real Celery ingestion in
    # tests, so insert the chunk directly with a fixed embedding matching the
    # fake embedding provider the `client` fixture wires up.
    db_session.add(
        DocumentChunk(
            document_id=document_id,
            chunk_index=0,
            content=content,
            embedding=[1.0] + [0.0] * 1535,
        )
    )
    await db_session.commit()


async def test_rag_search_returns_matching_chunks(client: AsyncClient, db_session: AsyncSession) -> None:
    document = await _create_document(client, content="Five years of backend engineering experience.")
    await _insert_chunk_for(db_session, document["id"], "Five years of backend engineering experience.")

    response = await client.post("/api/v1/rag/search", json={"query": "backend experience"})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["document_id"] == document["id"]
    assert results[0]["document_title"] == "My CV"


async def test_rag_search_with_no_documents_returns_empty(client: AsyncClient) -> None:
    response = await client.post("/api/v1/rag/search", json={"query": "anything"})

    assert response.status_code == 200
    assert response.json()["results"] == []


async def test_rag_ask_returns_answer_with_citations(client: AsyncClient, db_session: AsyncSession) -> None:
    document = await _create_document(client, content="Extensive Kubernetes experience.")
    await _insert_chunk_for(db_session, document["id"], "Extensive Kubernetes experience.")

    response = await client.post("/api/v1/rag/ask", json={"question": "Do I have Kubernetes experience?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Fake answer [1]."
    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_id"] == document["id"]


async def test_rag_ask_with_no_context_skips_generation(client: AsyncClient) -> None:
    response = await client.post("/api/v1/rag/ask", json={"question": "anything"})

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert "couldn't find" in body["answer"]
