from yoru_worker.runner import RetryingJobExecutor, WorkerRunner


class FakeProbe:
    def __init__(self) -> None:
        self.check_count = 0
        self.closed = False

    async def check(self) -> None:
        self.check_count += 1

    async def close(self) -> None:
        self.closed = True


class FakeJob:
    name = "fake-job"

    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.run_count = 0
        self.closed = False

    async def run_once(self) -> None:
        self.run_count += 1
        if self.run_count <= self.failures:
            raise RuntimeError("synthetic failure")

    async def close(self) -> None:
        self.closed = True


class FakeExecutor:
    def __init__(self) -> None:
        self.jobs: list[str] = []
        self.closed = False

    async def execute(self, job: FakeJob) -> bool:
        self.jobs.append(job.name)
        await job.run_once()
        return True

    async def close(self) -> None:
        self.closed = True


async def test_runner_executes_operational_jobs_after_probe() -> None:
    probe = FakeProbe()
    job = FakeJob()
    executor = FakeExecutor()
    runner = WorkerRunner(
        probe,
        poll_seconds=0.01,
        jobs=(job,),
        executor=executor,  # type: ignore[arg-type]
    )

    await runner.run_once()

    assert probe.check_count == 1
    assert job.run_count == 1
    assert executor.jobs == ["fake-job"]

    await runner.close()
    assert job.closed is True
    assert executor.closed is True
    assert probe.closed is True


async def test_retry_executor_retries_before_success() -> None:
    executor = RetryingJobExecutor(
        redis_url="redis://localhost:6379/15",
        max_attempts=3,
        retry_base_seconds=0,
        dead_letter_key="yoru:test:dead-letter",
    )
    job = FakeJob(failures=2)

    try:
        succeeded = await executor.execute(job)
    finally:
        await executor.close()

    assert succeeded is True
    assert job.run_count == 3
