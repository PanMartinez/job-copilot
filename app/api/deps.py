from typing import Annotated

from anthropic import AsyncAnthropic
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.dependencies import get_anthropic_client, get_db
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider

DbSession = Annotated[AsyncSession, Depends(get_db)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
AnthropicClientDep = Annotated[AsyncAnthropic, Depends(get_anthropic_client)]
