"""
MCP server entrypoint — exposes the Job Search Copilot service layer as tools.

Runs inside the `mcp` service in docker-compose.yml. A client (Claude Desktop/Code)
spawns this module fresh per session via `docker compose exec` — see app/mcp/README.md.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.config.db import async_session_factory
from app.mcp import handlers
from app.mcp.handlers import ToolError

mcp = FastMCP(
    "job-search-copilot",
    instructions=(
        "Tools for managing a personal job search: saved job postings, the application "
        "pipeline, and supporting documents (CVs, interview feedback, company research). "
        "All data lives in the user's own Job Copilot database - these tools search "
        "and store data the user has already saved, they do not browse the web or fetch "
        "live job listings themselves."
        "yet"
    ),
)


async def _run(handler: Callable[..., Awaitable[Any]], **kwargs: Any) -> Any:
    """Open a session, call a handler, and turn any failure into a friendly message."""
    try:
        async with async_session_factory() as db:
            return await handler(db, **kwargs)
    except ToolError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error: unexpected failure ({type(exc).__name__}: {exc})"


@mcp.tool()
async def search_jobs(
    query: Annotated[
        str | None, Field(description="Free-text search over job title, company, and description.")
    ] = None,
    location: Annotated[
        str | None, Field(description="Filter by location, partial match (e.g. 'Remote' or 'Gdańsk').")
    ] = None,
    status: Annotated[
        str | None, Field(description="Filter by exact job status (e.g. 'new', 'applied').")
    ] = None,
) -> list[dict[str, Any]] | str:
    """Search jobs already saved in the database. Does not search the web, only stored jobs."""
    return await _run(handlers.search_jobs, query=query, location=location, status=status)


@mcp.tool()
async def add_job(
    url: Annotated[str, Field(description="Link to the original job posting.")],
    title: Annotated[str, Field(description="Job title, e.g. 'Senior Backend Engineer'.")],
    company: Annotated[str, Field(description="Hiring company name.")],
    location: Annotated[
        str | None, Field(description="Job location, e.g. 'Remote' or 'Warszawa, Poland'.")
    ] = None,
    description: Annotated[str | None, Field(description="Full or partial job description text.")] = None,
    salary_min: Annotated[
        float | None, Field(description="Lower end of the advertised salary range.")
    ] = None,
    salary_max: Annotated[
        float | None, Field(description="Upper end of the advertised salary range.")
    ] = None,
    salary_currency: Annotated[
        str | None, Field(description="Currency code for the salary range, e.g. 'USD'.")
    ] = None,
) -> dict[str, Any] | str:
    """Save a job posting you found to the database.

    Returns a *job* id, distinct from an application id. Jobs and applications are separate
    records, so saving a job here does not put it in the pipeline. To move it into the
    pipeline (so it shows up under get_pipeline), call apply_to_job with this job's id.
    """
    return await _run(
        handlers.add_job,
        url=url,
        title=title,
        company=company,
        location=location,
        description=description,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
    )


@mcp.tool()
async def apply_to_job(
    job_id: Annotated[
        int,
        Field(description="The *job's* id, e.g. from add_job or search_jobs (not an application id)."),
    ],
    status: Annotated[
        str,
        Field(description="Pipeline status to set: draft, applied, interview, rejected, or offer."),
    ] = "applied",
    notes: Annotated[str | None, Field(description="Optional notes to attach to the application.")] = None,
) -> dict[str, Any] | str:
    """Move a saved job into the application pipeline.

    Creates the job's application record if it doesn't have one yet (defaulting to status
    "applied"), or updates the existing one if it already does - so it's safe to call again
    later to advance the same job's status. Use this when you only have a job id; if you
    already have an application id (e.g. from get_pipeline), update_application is more direct.
    """
    return await _run(handlers.apply_to_job, job_id=job_id, status=status, notes=notes)


@mcp.tool()
async def get_pipeline() -> dict[str, Any] | str:
    """Summarize all applications grouped by pipeline status (draft, applied, interview, rejected, offer)."""
    return await _run(handlers.get_pipeline)


@mcp.tool()
async def update_application(
    id: Annotated[
        int,
        Field(
            description="The *application's* id (from get_pipeline) - not a job id. "
            "If the job doesn't have an application yet, use apply_to_job instead."
        ),
    ],
    status: Annotated[
        str, Field(description="New pipeline status: draft, applied, interview, rejected, or offer.")
    ],
    notes: Annotated[
        str | None,
        Field(description="Notes to attach to the application. Replaces any existing notes."),
    ] = None,
) -> dict[str, Any] | str:
    """Move an existing application to a new pipeline stage, optionally updating its notes.

    Requires an application id, not a job id - if the job doesn't have an application yet
    (e.g. it was just saved with add_job), this will fail; use apply_to_job instead.
    """
    return await _run(handlers.update_application, application_id=id, status=status, notes=notes)


@mcp.tool()
async def add_document(
    type: Annotated[
        str, Field(description="Document type: cv, interview_feedback, company_research, or cover_letter.")
    ],
    title: Annotated[str, Field(description="Short descriptive title, e.g. 'Acme Corp - First Interview'.")],
    content: Annotated[str, Field(description="The document's full text content.")],
) -> dict[str, Any] | str:
    """Store a CV version, interview feedback, company research note, or a cover letter."""
    return await _run(handlers.add_document, doc_type=type, title=title, content=content)


@mcp.tool()
async def list_documents(
    type: Annotated[
        str | None,
        Field(description="Filter by document type: cv, interview_feedback, company_research, cover_letter."),
    ] = None,
) -> list[dict[str, Any]] | str:
    """List stored documents, optionally filtered by type."""
    return await _run(handlers.list_documents, doc_type=type)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
