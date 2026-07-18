import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApplicationStatus(enum.StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
