from celery import Celery

from app.config.settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "job_copilot",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["app.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_always_eager=_settings.celery_task_always_eager,
    timezone="UTC",
)
