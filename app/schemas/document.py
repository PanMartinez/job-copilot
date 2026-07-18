from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentType


class DocumentBase(BaseModel):
    type: DocumentType
    title: str
    content: str
    doc_metadata: dict | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    type: DocumentType | None = None
    title: str | None = None
    content: str | None = None
    doc_metadata: dict | None = None


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
