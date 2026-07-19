import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp import handlers
from app.mcp.handlers import ToolError

pytestmark = pytest.mark.asyncio


async def _add_job(db: AsyncSession, **overrides) -> dict:
    payload = {
        "url": "https://example.com/jobs/1",
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "location": "Remote",
        **overrides,
    }
    return await handlers.add_job(db, **payload)


async def test_add_job(db_session: AsyncSession) -> None:
    job = await _add_job(db_session)
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme Corp"
    assert job["status"] == "new"


async def test_search_jobs_by_query(db_session: AsyncSession) -> None:
    await _add_job(db_session, title="Senior Backend Engineer", company="Acme Corp")
    await _add_job(db_session, title="Frontend Engineer", company="Widget Co", location="Austin")

    results = await handlers.search_jobs(db_session, query="backend")
    assert len(results) == 1
    assert results[0]["company"] == "Acme Corp"


async def test_search_jobs_by_location(db_session: AsyncSession) -> None:
    await _add_job(db_session, title="Job A", location="Austin, TX")
    await _add_job(db_session, title="Job B", location="Remote")

    results = await handlers.search_jobs(db_session, location="austin")
    assert len(results) == 1
    assert results[0]["title"] == "Job A"


async def test_search_jobs_no_matches(db_session: AsyncSession) -> None:
    await _add_job(db_session, title="Job A")

    results = await handlers.search_jobs(db_session, query="nonexistent")
    assert results == []


async def test_get_pipeline_groups_by_status(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session, title="Platform Engineer", company="Beta Inc")
    await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"], notes="Applied via referral")
    )

    pipeline = await handlers.get_pipeline(db_session)
    assert "draft" in pipeline
    assert len(pipeline["draft"]) == 1
    entry = pipeline["draft"][0]
    assert entry["title"] == "Platform Engineer"
    assert entry["company"] == "Beta Inc"
    assert pipeline["applied"] == []


async def test_update_application_status(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session)
    application = await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"])
    )

    updated = await handlers.update_application(db_session, application.id, status="applied")
    assert updated["status"] == "applied"


async def test_update_application_preserves_notes_when_not_given(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session)
    application = await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"], notes="Original note")
    )

    updated = await handlers.update_application(db_session, application.id, status="applied")
    assert updated["notes"] == "Original note"


async def test_update_application_sets_notes_when_given(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session)
    application = await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"])
    )

    updated = await handlers.update_application(
        db_session, application.id, status="interview", notes="First call went well"
    )
    assert updated["notes"] == "First call went well"


async def test_apply_to_job_creates_application_and_shows_in_pipeline(db_session: AsyncSession) -> None:
    job = await _add_job(db_session, title="Platform Engineer", company="Beta Inc")

    applied = await handlers.apply_to_job(db_session, job_id=job["id"], status="applied")
    assert applied["job_id"] == job["id"]
    assert applied["status"] == "applied"

    pipeline = await handlers.get_pipeline(db_session)
    assert pipeline["applied"] == [
        {
            "application_id": applied["id"],
            "job_id": job["id"],
            "title": "Platform Engineer",
            "company": "Beta Inc",
            "notes": None,
            "updated_at": pipeline["applied"][0]["updated_at"],
        }
    ]
    for status, entries in pipeline.items():
        if status != "applied":
            assert entries == []


async def test_apply_to_job_defaults_to_applied_status(db_session: AsyncSession) -> None:
    job = await _add_job(db_session)

    application = await handlers.apply_to_job(db_session, job_id=job["id"])
    assert application["status"] == "applied"


async def test_apply_to_job_updates_existing_application_instead_of_duplicating(
    db_session: AsyncSession,
) -> None:
    job = await _add_job(db_session)

    first = await handlers.apply_to_job(db_session, job_id=job["id"], status="applied")
    second = await handlers.apply_to_job(
        db_session, job_id=job["id"], status="interview", notes="Recruiter call"
    )

    assert second["id"] == first["id"]
    assert second["status"] == "interview"
    assert second["notes"] == "Recruiter call"

    pipeline = await handlers.get_pipeline(db_session)
    assert pipeline["applied"] == []
    assert len(pipeline["interview"]) == 1


async def test_apply_to_job_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(ToolError, match="No job found"):
        await handlers.apply_to_job(db_session, job_id=999999, status="applied")


async def test_apply_to_job_invalid_status(db_session: AsyncSession) -> None:
    job = await _add_job(db_session)

    with pytest.raises(ToolError, match="not a valid application status"):
        await handlers.apply_to_job(db_session, job_id=job["id"], status="not_a_status")


async def test_apply_to_job_syncs_job_status(db_session: AsyncSession) -> None:
    job = await _add_job(db_session)

    await handlers.apply_to_job(db_session, job_id=job["id"], status="applied")

    results = await handlers.search_jobs(db_session, status="applied")
    assert [j["id"] for j in results] == [job["id"]]


async def test_update_application_syncs_job_status(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session)
    application = await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"])
    )

    await handlers.update_application(db_session, application.id, status="interview")

    results = await handlers.search_jobs(db_session, status="interview")
    assert [j["id"] for j in results] == [job["id"]]


async def test_update_application_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(ToolError, match="No application found"):
        await handlers.update_application(db_session, 999999, status="applied")


async def test_update_application_invalid_status(db_session: AsyncSession) -> None:
    from app.schemas.application import ApplicationCreate
    from app.services import application_service

    job = await _add_job(db_session)
    application = await application_service.create_application(
        db_session, ApplicationCreate(job_id=job["id"])
    )

    with pytest.raises(ToolError, match="not a valid application status"):
        await handlers.update_application(db_session, application.id, status="not_a_status")


async def test_add_document(db_session: AsyncSession) -> None:
    document = await handlers.add_document(
        db_session, doc_type="cv", title="My CV", content="Experienced backend engineer..."
    )
    assert document["type"] == "cv"
    assert document["title"] == "My CV"


async def test_add_document_invalid_type(db_session: AsyncSession) -> None:
    with pytest.raises(ToolError, match="not a valid document type"):
        await handlers.add_document(db_session, doc_type="not_a_type", title="X", content="Y")


async def test_list_documents_filters_by_type(db_session: AsyncSession) -> None:
    await handlers.add_document(db_session, doc_type="cv", title="My CV", content="...")
    await handlers.add_document(
        db_session, doc_type="interview_feedback", title="Acme feedback", content="Went well"
    )

    all_documents = await handlers.list_documents(db_session)
    assert len(all_documents) == 2

    cvs_only = await handlers.list_documents(db_session, doc_type="cv")
    assert len(cvs_only) == 1
    assert cvs_only[0]["title"] == "My CV"


async def test_list_documents_invalid_type(db_session: AsyncSession) -> None:
    with pytest.raises(ToolError, match="not a valid document type"):
        await handlers.list_documents(db_session, doc_type="not_a_type")
