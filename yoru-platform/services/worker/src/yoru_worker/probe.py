from typing import Protocol

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from yoru_worker.settings import WorkerSettings


class Probe(Protocol):
    async def check(self) -> None: ...

    async def close(self) -> None: ...


class InfrastructureProbe:
    def __init__(self, settings: WorkerSettings) -> None:
        self._engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
        self._redis = Redis.from_url(settings.redis_url, socket_timeout=3)

    async def check(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await self._redis.ping()

    async def close(self) -> None:
        await self._redis.aclose()
        await self._engine.dispose()
