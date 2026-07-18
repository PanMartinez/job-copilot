from fastapi import FastAPI

from app.api.routes import applications, documents, jobs
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(jobs.router, prefix=settings.api_v1_prefix)
app.include_router(applications.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
