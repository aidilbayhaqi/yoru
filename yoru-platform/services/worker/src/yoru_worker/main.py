import argparse
import asyncio
import signal
from contextlib import suppress

from yoru_worker.logging import configure_logging
from yoru_worker.probe import InfrastructureProbe
from yoru_worker.runner import WorkerRunner
from yoru_worker.settings import WorkerSettings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Yoru worker foundation")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one infrastructure probe and exit.",
    )
    return parser.parse_args()


async def async_main(run_once: bool) -> None:
    settings = WorkerSettings()
    configure_logging(settings.log_level)
    runner = WorkerRunner(InfrastructureProbe(settings), settings.worker_poll_seconds)

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
