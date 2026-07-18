from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRead, status_code=201)
async def create_document(data: DocumentCreate, db: DbSession) -> DocumentRead:
    document = await document_service.create_document(db, data)
    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
async def list_documents(db: DbSession, limit: int = 100, offset: int = 0) -> list[DocumentRead]:
    documents = await document_service.list_documents(db, limit=limit, offset=offset)
    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(document_id: int, db: DbSession) -> DocumentRead:
    document = await document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentRead.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(document_id: int, data: DocumentUpdate, db: DbSession) -> DocumentRead:
    document = await document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    document = await document_service.update_document(db, document, data)
    return DocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: int, db: DbSession) -> None:
    document = await document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await document_service.delete_document(db, document)
