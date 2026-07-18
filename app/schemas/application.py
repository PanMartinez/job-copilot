from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationBase(BaseModel):
    job_id: int
    status: ApplicationStatus = ApplicationStatus.DRAFT
    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
