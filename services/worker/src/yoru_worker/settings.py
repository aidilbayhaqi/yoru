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

    booking_maintenance_enabled: bool = True
    booking_maintenance_batch_size: int = Field(default=100, ge=1, le=1000)
    booking_auto_no_show_enabled: bool = False
    booking_auto_no_show_grace_minutes: int = Field(default=120, ge=15, le=10_080)
    booking_tracking_ping_retention_days: int = Field(default=30, ge=1, le=3650)

    worker_job_max_attempts: int = Field(default=3, ge=1, le=10)
    worker_job_retry_base_seconds: float = Field(default=0.5, ge=0, le=30)
    worker_dead_letter_key: str = Field(
        default="yoru:worker:dead-letter",
        min_length=3,
        max_length=200,
    )
