from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobBase(BaseModel):
    title: str
    company: str
    location: str | None = None
    url: str | None = None
    source: str | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    posted_at: datetime | None = None
    status: str = "new"


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    url: str | None = None
    source: str | None = None
    description: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    posted_at: datetime | None = None
    status: str | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
