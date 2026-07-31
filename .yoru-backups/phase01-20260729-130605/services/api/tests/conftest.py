from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yoru_api.core.checks import CheckResult
from yoru_api.core.settings import Settings
from yoru_api.main import create_app


class HealthyChecker:
    async def check_all(self) -> dict[str, CheckResult]:
        return {
            "postgres": CheckResult(status="ok", latency_ms=1.1),
            "redis": CheckResult(status="ok", latency_ms=0.7),
            "qdrant": CheckResult(status="ok", latency_ms=1.4),
        }


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        database_url="postgresql+asyncpg://yoru:test@localhost:5432/yoru_test",
        cors_allowed_origins="http://localhost:3000,http://localhost:3001",
        trusted_hosts="testserver,localhost",
        session_signing_key="test-session-key-not-for-production",
        refresh_token_pepper="test-refresh-pepper-not-for-production",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    app = create_app(settings)
    app.state.health_checker = HealthyChecker()
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
