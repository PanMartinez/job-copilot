import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentType
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.tasks.ingestion import ingest_document as ingest_document_task

logger = logging.getLogger(__name__)


def _queue_ingestion(document_id: int) -> None:
    """
    a document save must succeed even if the broker
    (Redis/Celery) is unreachable - the document just won't be searchable via
    RAG until ingestion runs later, e.g. once a worker/broker is available.
    """
    try:
        ingest_document_task.delay(document_id)
    except Exception:
        logger.warning("Failed to queue RAG ingestion for document %s", document_id, exc_info=True)


async def create_document(db: AsyncSession, data: DocumentCreate) -> Document:
    document = Document(**data.model_dump())
    db.add(document)
    await db.commit()
    await db.refresh(document)
    _queue_ingestion(document.id)
    return document


async def list_documents(
    db: AsyncSession,
    doc_type: DocumentType | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Document]:
    stmt = select(Document).order_by(Document.id)
    if doc_type is not None:
        stmt = stmt.where(Document.type == doc_type)
    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: int) -> Document | None:
    return await db.get(Document, document_id)


async def update_document(db: AsyncSession, document: Document, data: DocumentUpdate) -> Document:
    changed_fields = data.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    if "content" in changed_fields:
        _queue_ingestion(document.id)
    return document


async def delete_document(db: AsyncSession, document: Document) -> None:
    await db.delete(document)
    await db.commit()
