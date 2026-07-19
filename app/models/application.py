import enum

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ApplicationStatus(enum.StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class Application(BaseModel):
    __tablename__ = "applications"

    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=ApplicationStatus.DRAFT,
        server_default=ApplicationStatus.DRAFT.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)
