import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Protocol

from redis.asyncio import Redis

from yoru_worker.probe import Probe

logger = logging.getLogger("yoru_worker")


class WorkerJob(Protocol):
    @property
    def name(self) -> str: ...

    async def run_once(self) -> object: ...

    async def close(self) -> None: ...


class RetryingJobExecutor:
    def __init__(
        self,
        *,
        redis_url: str,
        max_attempts: int,
        retry_base_seconds: float,
        dead_letter_key: str,
    ) -> None:
        self._redis = Redis.from_url(redis_url, socket_timeout=3)
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds
        self._dead_letter_key = dead_letter_key

    async def execute(self, job: WorkerJob) -> bool:
        for attempt in range(1, self._max_attempts + 1):
            try:
                await job.run_once()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.exception(
                    "worker_job_attempt_failed",
                    extra={"job": job.name, "attempt": attempt},
                )
                if attempt < self._max_attempts:
                    await asyncio.sleep(self._retry_base_seconds * (2 ** (attempt - 1)))
                    continue
                await self._dead_letter(job=job, error=error, attempts=attempt)
                return False
            else:
                logger.info("worker_job_succeeded", extra={"job": job.name})
                return True
        return False

    async def _dead_letter(
        self,
        *,
        job: WorkerJob,
        error: Exception,
        attempts: int,
    ) -> None:
        payload = {
            "job": job.name,
            "attempts": attempts,
            "error_type": type(error).__name__,
            "failed_at": datetime.now(UTC).isoformat(),
        }
        try:
            await self._redis.lpush(self._dead_letter_key, json.dumps(payload))
            await self._redis.ltrim(self._dead_letter_key, 0, 999)
        except Exception:
            logger.exception("worker_dead_letter_write_failed", extra={"job": job.name})

    async def close(self) -> None:
        await self._redis.aclose()


class WorkerRunner:
    def __init__(
        self,
        probe: Probe,
        poll_seconds: float,
        *,
        jobs: tuple[WorkerJob, ...] = (),
        executor: RetryingJobExecutor | None = None,
    ) -> None:
        self._probe = probe
        self._poll_seconds = poll_seconds
        self._jobs = jobs
        self._executor = executor
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def close(self) -> None:
        for job in self._jobs:
            await job.close()
        if self._executor is not None:
            await self._executor.close()
        await self._probe.close()

    async def run_once(self) -> None:
        await self._probe.check()
        logger.info("foundation_probe_succeeded")
        for job in self._jobs:
            if self._executor is None:
                await job.run_once()
            else:
                await self._executor.execute(job)

    async def run_forever(self) -> None:
        logger.info("worker_started")
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("worker_cycle_failed")
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._poll_seconds,
                    )
                except TimeoutError:
                    continue
        finally:
            await self.close()
            logger.info("worker_stopped")
