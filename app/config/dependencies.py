from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.db import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


def get_anthropic_client() -> AsyncAnthropic:
    return AsyncAnthropic()
