from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.db import Base
from app.config.dependencies import get_anthropic_client, get_db
from app.config.settings import get_settings
from app.main import app
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider

_EMBEDDING_DIM = 1536


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic, network-free stand-in for the real OpenAI provider."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * (_EMBEDDING_DIM - 1) for _ in texts]


class _FakeAnthropicClient:
    """Deterministic, network-free stand-in for the real Anthropic client."""

    def __init__(self) -> None:
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Fake answer [1].")])


_settings = get_settings()
# A separate physical database from the dev one, so tests never touch real data.
# It must already exist with the `vector` extension enabled - see README.
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{_settings.db_user}:{_settings.db_password}"
    f"@{_settings.db_host}:{_settings.db_port}/{_settings.db_name}_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
def _stub_ingestion_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the test suite from touching Celery/Redis. RAG-specific ingestion
    tests call app.rag.ingestion.ingest_document(...) directly instead."""
    monkeypatch.setattr("app.services.document_service.ingest_document_task.delay", lambda *a, **k: None)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_provider] = lambda: _FakeEmbeddingProvider()
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropicClient()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
