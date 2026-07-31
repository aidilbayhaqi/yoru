import asyncio
import logging

from yoru_worker.probe import Probe

logger = logging.getLogger("yoru_worker")


class WorkerRunner:
    def __init__(self, probe: Probe, poll_seconds: float) -> None:
        self._probe = probe
        self._poll_seconds = poll_seconds
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def close(self) -> None:
        await self._probe.close()

    async def run_once(self) -> None:
        await self._probe.check()
        logger.info("foundation_probe_succeeded")

    async def run_forever(self) -> None:
        logger.info("worker_started")
        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except Exception:
                    logger.exception("foundation_probe_failed")
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
