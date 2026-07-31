import asyncio
import time
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Protocol

import httpx
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from yoru_api.core.settings import Settings


@dataclass(frozen=True, slots=True)
class CheckResult:
    status: str
    latency_ms: float


class HealthChecker(Protocol):
    async def check_all(self) -> dict[str, CheckResult]: ...


class DependencyHealthChecker:
    def __init__(self, settings: Settings, engine: AsyncEngine) -> None:
        self._settings = settings
        self._engine = engine

    async def _timed_check(self, check: Awaitable[None]) -> CheckResult:
        started = time.perf_counter()
        status = "ok"
        try:
            await check
        except Exception:
            status = "unavailable"
        return CheckResult(
            status=status,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    async def _check_database(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def _check_redis(self) -> None:
        client = Redis.from_url(self._settings.redis_url, socket_timeout=2)
        try:
            await client.ping()
        finally:
            await client.aclose()

    async def _check_qdrant(self) -> None:
        headers: dict[str, str] = {}
        if self._settings.qdrant_api_key:
            headers["api-key"] = self._settings.qdrant_api_key.get_secret_value()
        async with httpx.AsyncClient(
            timeout=min(self._settings.request_timeout_seconds, 3),
            headers=headers,
        ) as client:
            response = await client.get(f"{str(self._settings.qdrant_url).rstrip('/')}/readyz")
            response.raise_for_status()

    async def check_all(self) -> dict[str, CheckResult]:
        database, redis, qdrant = await asyncio.gather(
            self._timed_check(self._check_database()),
            self._timed_check(self._check_redis()),
            self._timed_check(self._check_qdrant()),
        )
        return {
            "postgres": database,
            "redis": redis,
            "qdrant": qdrant,
        }
