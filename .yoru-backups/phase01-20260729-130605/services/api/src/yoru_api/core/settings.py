from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "Yoru"
    app_version: str = "0.2.0"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://yoru:yoru_local_only@localhost:5432/yoru"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: AnyHttpUrl = AnyHttpUrl("http://localhost:6333")
    qdrant_api_key: SecretStr | None = None

    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:3001",
    )
    trusted_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver", "api")
    request_timeout_seconds: float = Field(default=30, gt=0, le=120)
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    refresh_token_ttl_seconds: int = Field(default=2_592_000, ge=3600, le=7_776_000)
    auth_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    auth_rate_limit_window_seconds: int = Field(default=300, ge=10, le=3600)
    cookie_secure: bool = False
    cookie_domain: str | None = None

    session_signing_key: SecretStr = SecretStr("local-development-key-change-before-production")
    refresh_token_pepper: SecretStr = SecretStr("local-development-pepper-change-before-production")

    feature_customer_ai: bool = False
    feature_partner_copilot: bool = False
    feature_live_tracking: bool = False
    feature_dental_service: bool = False

    @field_validator("cors_allowed_origins", "trusted_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def empty_cookie_domain_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/' and not end with '/'")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if "*" in value:
            raise ValueError("Wildcard CORS origin is not allowed")
        for origin in value:
            parsed = AnyHttpUrl(origin)
            if parsed.path not in ("", "/"):
                raise ValueError("CORS origins must not include a path")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env != "production":
            return self

        forbidden_fragments = ("local-development", "change-before-production")
        secret_values = (
            self.session_signing_key.get_secret_value(),
            self.refresh_token_pepper.get_secret_value(),
        )
        if any(fragment in secret for secret in secret_values for fragment in forbidden_fragments):
            raise ValueError("Production secrets still use local placeholder values")
        if any(len(secret) < 32 for secret in secret_values):
            raise ValueError(
                "Production authentication secrets must contain at least 32 characters"
            )
        if any("localhost" in origin for origin in self.cors_allowed_origins):
            raise ValueError("Production CORS origins cannot use localhost")
        if not self.cookie_secure:
            raise ValueError("Production cookies must be secure")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
