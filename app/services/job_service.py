from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.schemas.job import JobCreate, JobUpdate


async def create_job(db: AsyncSession, data: JobCreate) -> Job:
    job = Job(**data.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_jobs(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Job]:
    result = await db.execute(select(Job).order_by(Job.id).limit(limit).offset(offset))
    return list(result.scalars().all())


async def search_jobs(
    db: AsyncSession,
    query: str | None = None,
    location: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[Job]:
    stmt = select(Job).order_by(Job.id)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(Job.title.ilike(pattern), Job.company.ilike(pattern), Job.description.ilike(pattern))
        )
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if status:
        stmt = stmt.where(Job.status == status)
    result = await db.execute(stmt.limit(limit))
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: int) -> Job | None:
    return await db.get(Job, job_id)


async def update_job(db: AsyncSession, job: Job, data: JobUpdate) -> Job:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


async def delete_job(db: AsyncSession, job: Job) -> None:
    await db.delete(job)
    await db.commit()
