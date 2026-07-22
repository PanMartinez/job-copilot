from abc import ABC, abstractmethod
from functools import lru_cache

from openai import AsyncOpenAI

from app.config.settings import get_settings
from app.models.document import EMBEDDING_DIM

EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingProvider(ABC):
    dimension: int = EMBEDDING_DIM

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input in the same order."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key or get_settings().openai_api_key)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider()
