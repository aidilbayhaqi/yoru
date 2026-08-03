from yoru_worker.settings import WorkerSettings


def test_booking_maintenance_defaults_are_safe() -> None:
    settings = WorkerSettings(_env_file=None)

    assert settings.booking_maintenance_enabled is True
    assert settings.booking_auto_no_show_enabled is False
    assert settings.booking_tracking_ping_retention_days == 30
    assert settings.worker_job_max_attempts == 3
