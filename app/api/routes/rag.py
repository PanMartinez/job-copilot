from fastapi import APIRouter

from app.api.deps import AnthropicClientDep, DbSession, EmbeddingProviderDep
from app.schemas.rag import (
    AskRequest,
    AskResponse,
    CitationRead,
    RetrievedChunkRead,
    SearchRequest,
    SearchResponse,
)
from app.services import answer_service, retrieval_service

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=SearchResponse)
async def search(
    data: SearchRequest, db: DbSession, embedding_provider: EmbeddingProviderDep
) -> SearchResponse:
    results = await retrieval_service.hybrid_search(
        db, data.query, max_chunks=data.max_chunks, embedding_provider=embedding_provider
    )
    return SearchResponse(
        results=[
            RetrievedChunkRead(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_title=r.document_title,
                document_type=r.document_type,
                content=r.content,
                rrf_score=r.rrf_score,
            )
            for r in results
        ]
    )


@router.post("/ask", response_model=AskResponse)
async def ask(
    data: AskRequest,
    db: DbSession,
    embedding_provider: EmbeddingProviderDep,
    client: AnthropicClientDep,
) -> AskResponse:
    result = await answer_service.answer_question(
        db, data.question, max_chunks=data.max_chunks, embedding_provider=embedding_provider, client=client
    )
    return AskResponse(
        answer=result.answer,
        citations=[
            CitationRead(
                document_id=c.document_id,
                document_title=c.document_title,
                document_type=c.document_type,
                chunk_id=c.chunk_id,
            )
            for c in result.citations
        ],
    )
