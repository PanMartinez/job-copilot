from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
async def create_job(data: JobCreate, db: DbSession) -> JobRead:
    job = await job_service.create_job(db, data)
    return JobRead.model_validate(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(db: DbSession, limit: int = 100, offset: int = 0) -> list[JobRead]:
    jobs = await job_service.list_jobs(db, limit=limit, offset=offset)
    return [JobRead.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, db: DbSession) -> JobRead:
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRead.model_validate(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(job_id: int, data: JobUpdate, db: DbSession) -> JobRead:
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = await job_service.update_job(db, job, data)
    return JobRead.model_validate(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, db: DbSession) -> None:
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    await job_service.delete_job(db, job)
