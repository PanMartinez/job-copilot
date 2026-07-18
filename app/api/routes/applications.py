from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas.application import ApplicationCreate, ApplicationRead, ApplicationUpdate
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationRead, status_code=201)
async def create_application(data: ApplicationCreate, db: DbSession) -> ApplicationRead:
    application = await application_service.create_application(db, data)
    return ApplicationRead.model_validate(application)


@router.get("", response_model=list[ApplicationRead])
async def list_applications(db: DbSession, limit: int = 100, offset: int = 0) -> list[ApplicationRead]:
    applications = await application_service.list_applications(db, limit=limit, offset=offset)
    return [ApplicationRead.model_validate(application) for application in applications]


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(application_id: int, db: DbSession) -> ApplicationRead:
    application = await application_service.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationRead.model_validate(application)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(application_id: int, data: ApplicationUpdate, db: DbSession) -> ApplicationRead:
    application = await application_service.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application = await application_service.update_application(db, application, data)
    return ApplicationRead.model_validate(application)


@router.delete("/{application_id}", status_code=204)
async def delete_application(application_id: int, db: DbSession) -> None:
    application = await application_service.get_application(db, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    await application_service.delete_application(db, application)
