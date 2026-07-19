"""Tool handlers backing the MCP server.

Each function is a thin, directly-testable wrapper around the existing
service layer (`app/services/*_service.py`) — no business logic lives here,
only translation between MCP-tool-shaped arguments/results and the service
calls. Expected, user-facing failures (bad input, not found) are raised as
`ToolError`, which `app/mcp/server.py` turns into a friendly message instead
of letting a raw exception reach the LLM.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.document import DocumentType
from app.models.job import Job
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.document import DocumentCreate
from app.schemas.job import JobCreate, JobUpdate
from app.services import application_service, document_service, job_service


class ToolError(Exception):
    """An expected, user-facing tool failure (bad input, not found, etc.)."""


def _job_to_dict(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "status": job.status,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
    }


async def search_jobs(
    db: AsyncSession,
    query: str | None = None,
    location: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    jobs = await job_service.search_jobs(db, query=query, location=location, status=status)
    return [_job_to_dict(job) for job in jobs]


async def add_job(
    db: AsyncSession,
    url: str,
    title: str,
    company: str,
    location: str | None = None,
    description: str | None = None,
    salary_min: float | None = None,
    salary_max: float | None = None,
    salary_currency: str | None = None,
) -> dict[str, Any]:
    data = JobCreate(
        url=url,
        title=title,
        company=company,
        location=location,
        description=description,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
    )
    job = await job_service.create_job(db, data)
    return _job_to_dict(job)


def _application_to_dict(application: Application) -> dict[str, Any]:
    return {
        "id": application.id,
        "job_id": application.job_id,
        "status": application.status.value,
        "notes": application.notes,
    }


async def apply_to_job(
    db: AsyncSession,
    job_id: int,
    status: str = "applied",
    notes: str | None = None,
) -> dict[str, Any]:
    """Create (or update) the application for a saved job, moving it into the pipeline."""
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise ToolError(f"No job found with id {job_id}.")

    status_value = _parse_application_status(status)

    application = await application_service.get_application_by_job_id(db, job_id)
    if application is None:
        application = await application_service.create_application(
            db, ApplicationCreate(job_id=job_id, status=status_value, notes=notes)
        )
    else:
        update_fields: dict[str, Any] = {"status": status_value}
        if notes is not None:
            update_fields["notes"] = notes
        application = await application_service.update_application(
            db, application, ApplicationUpdate(**update_fields)
        )

    await job_service.update_job(db, job, JobUpdate(status=status_value.value))

    return _application_to_dict(application)


async def get_pipeline(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    pipeline = await application_service.get_pipeline(db)
    return {
        status.value: [{**entry, "updated_at": entry["updated_at"].isoformat()} for entry in entries]
        for status, entries in pipeline.items()
    }


def _parse_application_status(raw: str) -> ApplicationStatus:
    try:
        return ApplicationStatus(raw.lower())
    except ValueError as exc:
        valid = ", ".join(s.value for s in ApplicationStatus)
        raise ToolError(f"'{raw}' is not a valid application status. Valid options: {valid}.") from exc


def _parse_document_type(raw: str) -> DocumentType:
    try:
        return DocumentType(raw.lower())
    except ValueError as exc:
        valid = ", ".join(t.value for t in DocumentType)
        raise ToolError(f"'{raw}' is not a valid document type. Valid options: {valid}.") from exc


async def update_application(
    db: AsyncSession,
    application_id: int,
    status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    application = await application_service.get_application(db, application_id)
    if application is None:
        raise ToolError(f"No application found with id {application_id}.")

    status_value = _parse_application_status(status)
    update_fields: dict[str, Any] = {"status": status_value}
    if notes is not None:
        update_fields["notes"] = notes

    application = await application_service.update_application(
        db, application, ApplicationUpdate(**update_fields)
    )

    job = await job_service.get_job(db, application.job_id)
    if job is not None:
        await job_service.update_job(db, job, JobUpdate(status=status_value.value))

    return _application_to_dict(application)


async def add_document(db: AsyncSession, doc_type: str, title: str, content: str) -> dict[str, Any]:
    document = await document_service.create_document(
        db, DocumentCreate(type=_parse_document_type(doc_type), title=title, content=content)
    )
    return {"id": document.id, "type": document.type.value, "title": document.title}


async def list_documents(db: AsyncSession, doc_type: str | None = None) -> list[dict[str, Any]]:
    parsed_type = _parse_document_type(doc_type) if doc_type is not None else None
    documents = await document_service.list_documents(db, doc_type=parsed_type)
    return [
        {
            "id": d.id,
            "type": d.type.value,
            "title": d.title,
            "created_at": d.created_at.isoformat(),
        }
        for d in documents
    ]
