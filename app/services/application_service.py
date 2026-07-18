from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate


async def create_application(db: AsyncSession, data: ApplicationCreate) -> Application:
    application = Application(**data.model_dump())
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def list_applications(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Application]:
    result = await db.execute(select(Application).order_by(Application.id).limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_application(db: AsyncSession, application_id: int) -> Application | None:
    return await db.get(Application, application_id)


async def update_application(
    db: AsyncSession, application: Application, data: ApplicationUpdate
) -> Application:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    await db.commit()
    await db.refresh(application)
    return application


async def delete_application(db: AsyncSession, application: Application) -> None:
    await db.delete(application)
    await db.commit()
