import argparse
import asyncio
import signal
from contextlib import suppress

from yoru_worker.booking_maintenance import BookingMaintenanceJob
from yoru_worker.logging import configure_logging
from yoru_worker.probe import InfrastructureProbe
from yoru_worker.runner import RetryingJobExecutor, WorkerRunner
from yoru_worker.settings import WorkerSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Yoru operational worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one infrastructure check and one maintenance cycle, then exit.",
    )
    return parser.parse_args()


async def async_main(run_once: bool) -> None:
    settings = WorkerSettings()
    configure_logging(settings.log_level)

    jobs = (
        (BookingMaintenanceJob(settings),)
        if settings.booking_maintenance_enabled
        else ()
    )
    executor = (
        RetryingJobExecutor(
            redis_url=settings.redis_url,
            max_attempts=settings.worker_job_max_attempts,
            retry_base_seconds=settings.worker_job_retry_base_seconds,
            dead_letter_key=settings.worker_dead_letter_key,
        )
        if jobs
        else None
    )
    runner = WorkerRunner(
        InfrastructureProbe(settings),
        settings.worker_poll_seconds,
        jobs=jobs,
        executor=executor,
    )
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGTERM, signal.SIGINT):
        # Windows' Proactor event loop does not expose signal handlers.
        with suppress(NotImplementedError):
            loop.add_signal_handler(signal_name, runner.stop)

    if run_once:
        try:
            await runner.run_once()
        finally:
            await runner.close()
        return

    await runner.run_forever()


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args.once))


if __name__ == "__main__":
    main()
