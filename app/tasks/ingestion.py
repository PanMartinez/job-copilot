import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.celery_app import celery_app
from app.config.settings import get_settings
from app.rag.ingestion import ingest_document as _ingest_document_async


async def _run(document_id: int) -> int:
    # A dedicated, NullPool engine per invocation rather than the shared
    # app.config.db engine: asyncpg connection pools are bound to the event
    # loop that created them, and asyncio.run() below creates and tears down a
    # fresh loop on every call. Reusing a long-lived pool across repeated
    # asyncio.run() calls in a worker process risks "attached to a different
    # loop" errors once earlier loops are gone. One extra connection per
    # ingestion call is a fine cost for a per-document background task.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            return await _ingest_document_async(db, document_id)
    finally:
        await engine.dispose()


@celery_app.task(name="app.tasks.ingestion.ingest_document", max_retries=3, default_retry_delay=30)
def ingest_document(document_id: int) -> int:
    return asyncio.run(_run(document_id))
