from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentType
from app.rag.embeddings import EmbeddingProvider
from app.schemas.job import JobCreate
from app.services import answer_service, job_service
from app.services.answer_service import JobNotFoundError

pytestmark = pytest.mark.asyncio

_DIM = 1536
# A fixed, non-zero unit vector: pgvector's cosine_distance is undefined (and
# errors) for the zero vector, so query and chunk embeddings both use this.
_VECTOR = [1.0] + [0.0] * (_DIM - 1)


class _FakeEmbeddingProvider(EmbeddingProvider):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_VECTOR for _ in texts]


class _FakeAnthropicClient:
    def __init__(self, text: str = "Fake answer [1].") -> None:
        self.calls: list[dict] = []
        self._text = text
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._text)])


async def _add_document_with_chunk(db: AsyncSession, *, title: str, content: str) -> Document:
    document = Document(type=DocumentType.CV, title=title, content=content)
    db.add(document)
    await db.commit()
    db.add(DocumentChunk(document_id=document.id, chunk_index=0, content=content, embedding=_VECTOR))
    await db.commit()
    return document


async def test_answer_question_calls_anthropic_with_retrieved_context(db_session: AsyncSession) -> None:
    await _add_document_with_chunk(db_session, title="My CV", content="Five years of backend experience.")
    client = _FakeAnthropicClient("You're a strong fit [1].")

    result = await answer_service.answer_question(
        db_session,
        "What's my backend experience?",
        embedding_provider=_FakeEmbeddingProvider(),
        client=client,
    )

    assert result.answer == "You're a strong fit [1]."
    assert len(result.citations) == 1
    assert result.citations[0].document_title == "My CV"
    assert len(client.calls) == 1
    assert "backend experience" in client.calls[0]["system"]


async def test_answer_question_skips_anthropic_when_no_context_found(db_session: AsyncSession) -> None:
    client = _FakeAnthropicClient()

    result = await answer_service.answer_question(
        db_session, "anything", embedding_provider=_FakeEmbeddingProvider(), client=client
    )

    assert result.citations == []
    assert client.calls == []  # the no-context fallback path never calls Anthropic


async def test_match_job_to_profile_not_found(db_session: AsyncSession) -> None:
    client = _FakeAnthropicClient()

    with pytest.raises(JobNotFoundError):
        await answer_service.match_job_to_profile(
            db_session, 999999, embedding_provider=_FakeEmbeddingProvider(), client=client
        )
    assert client.calls == []


async def test_match_job_to_profile_builds_fit_analysis(db_session: AsyncSession) -> None:
    await _add_document_with_chunk(
        db_session,
        title="My CV",
        content="Extensive Kubernetes and distributed systems experience.",
    )
    job = await job_service.create_job(
        db_session,
        JobCreate(title="Platform Engineer", company="Acme", description="Own our Kubernetes platform."),
    )
    client = _FakeAnthropicClient("Great match [1].")

    result = await answer_service.match_job_to_profile(
        db_session, job.id, embedding_provider=_FakeEmbeddingProvider(), client=client
    )

    assert result.answer == "Great match [1]."
    assert len(result.citations) == 1
    assert result.citations[0].document_title == "My CV"
    assert len(client.calls) == 1
