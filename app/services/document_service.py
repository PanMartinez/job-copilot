from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


async def create_document(db: AsyncSession, data: DocumentCreate) -> Document:
    document = Document(**data.model_dump())
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Document]:
    result = await db.execute(select(Document).order_by(Document.id).limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: int) -> Document | None:
    return await db.get(Document, document_id)


async def update_document(db: AsyncSession, document: Document, data: DocumentUpdate) -> Document:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    return document


async def delete_document(db: AsyncSession, document: Document) -> None:
    await db.delete(document)
    await db.commit()
