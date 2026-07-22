"""RAG "answer" service: retrieve context, ask Claude, return an answer with
citations back to the source documents.
"""

from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import EmbeddingProvider
from app.services import job_service, retrieval_service
from app.services.retrieval_service import RetrievedChunk

ANSWER_MODEL = "claude-opus-4-8"

_NO_CONTEXT_ANSWER = "I couldn't find anything in your saved documents relevant to that question."

_ANSWER_SYSTEM_PROMPT = (
    "You are a job-search assistant answering a question using only the excerpts "
    "from the user's own documents (CVs, interview feedback, company research) "
    "given below. Cite the excerpt(s) you used with bracketed numbers like [1], "
    "matching the numbering in the context. If the context doesn't contain enough "
    "information to answer, say so plainly instead of guessing.\n\nContext:\n{context}"
)

_MATCH_JOB_SYSTEM_PROMPT = (
    "You are a job-search assistant. Given a job description and excerpts from the "
    "user's own CV/experience documents below, produce a fit analysis covering: "
    "(1) matching qualifications, (2) notable gaps, (3) an overall recommendation. "
    "Cite the excerpt(s) you used with bracketed numbers like [1], matching the "
    "numbering in the context. Base your analysis only on the excerpts given - "
    "don't invent experience that isn't there.\n\nContext:\n{context}"
)


class JobNotFoundError(Exception):
    """Raised by match_job_to_profile when the job id doesn't exist."""


@dataclass
class Citation:
    document_id: int
    document_title: str
    document_type: str
    chunk_id: int


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]


def _citations_from(chunks: list[RetrievedChunk]) -> list[Citation]:
    return [
        Citation(
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            document_type=chunk.document_type,
            chunk_id=chunk.chunk_id,
        )
        for chunk in chunks
    ]


def _build_context_block(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{i}] {chunk.document_title} ({chunk.document_type}):\n{chunk.content}"
        for i, chunk in enumerate(chunks, start=1)
    )


async def _call_anthropic(client: Any, system: str, question: str) -> str:
    response = await client.messages.create(
        model=ANSWER_MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return next((block.text for block in response.content if block.type == "text"), "")


async def answer_question(
    db: AsyncSession,
    question: str,
    *,
    max_chunks: int = 8,
    embedding_provider: EmbeddingProvider | None = None,
    client: Any = None,
) -> AnswerResult:
    chunks = await retrieval_service.hybrid_search(
        db, question, max_chunks=max_chunks, embedding_provider=embedding_provider
    )
    if not chunks:
        return AnswerResult(answer=_NO_CONTEXT_ANSWER, citations=[])

    system = _ANSWER_SYSTEM_PROMPT.format(context=_build_context_block(chunks))
    answer = await _call_anthropic(client or AsyncAnthropic(), system, question)
    return AnswerResult(answer=answer, citations=_citations_from(chunks))


async def match_job_to_profile(
    db: AsyncSession,
    job_id: int,
    *,
    max_chunks: int = 8,
    embedding_provider: EmbeddingProvider | None = None,
    client: Any = None,
) -> AnswerResult:
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise JobNotFoundError(f"No job found with id {job_id}.")

    retrieval_query = f"{job.title} at {job.company}\n\n{job.description or ''}".strip()
    chunks = await retrieval_service.hybrid_search(
        db, retrieval_query, max_chunks=max_chunks, embedding_provider=embedding_provider
    )
    if not chunks:
        return AnswerResult(answer=_NO_CONTEXT_ANSWER, citations=[])

    system = _MATCH_JOB_SYSTEM_PROMPT.format(context=_build_context_block(chunks))
    question = f"How well does my background fit this job?\n\n{retrieval_query}"
    answer = await _call_anthropic(client or AsyncAnthropic(), system, question)
    return AnswerResult(answer=answer, citations=_citations_from(chunks))
