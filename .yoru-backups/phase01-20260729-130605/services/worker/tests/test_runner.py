from yoru_worker.runner import WorkerRunner


class FakeProbe:
    def __init__(self) -> None:
        self.check_count = 0
        self.closed = False

    async def check(self) -> None:
        self.check_count += 1

    async def close(self) -> None:
        self.closed = True


async def test_run_once_executes_one_probe() -> None:
    probe = FakeProbe()
    runner = WorkerRunner(probe, poll_seconds=0.01)

    await runner.run_once()

    assert probe.check_count == 1
    assert probe.closed is False


async def test_runner_stops_and_closes_probe() -> None:
    probe = FakeProbe()
    runner = WorkerRunner(probe, poll_seconds=0.01)
    runner.stop()

    await runner.run_forever()

    assert probe.check_count == 0
    assert probe.closed is True
