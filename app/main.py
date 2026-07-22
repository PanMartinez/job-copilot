from fastapi import FastAPI

from app.api.routes import applications, documents, jobs, rag
from app.config.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.include_router(jobs.router, prefix=settings.api_v1_prefix)
app.include_router(applications.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)
app.include_router(rag.router, prefix=settings.api_v1_prefix)


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "pong"}
