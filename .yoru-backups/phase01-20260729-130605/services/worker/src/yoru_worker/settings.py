from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://yoru:yoru_local_only@localhost:5432/yoru"
    redis_url: str = "redis://localhost:6379/0"
    worker_poll_seconds: float = Field(default=5, gt=0, le=300)
