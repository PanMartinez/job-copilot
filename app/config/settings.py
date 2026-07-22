from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Job Search Copilot"
    api_v1_prefix: str = "/api/v1"

    allowed_hosts: str = "*"

    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False

    model_config = SettingsConfigDict(env_file="app/config/.env", env_file_encoding="utf-8", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{int(self.db_port)}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
