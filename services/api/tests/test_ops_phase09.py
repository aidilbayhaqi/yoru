from datetime import UTC, datetime, timedelta

from yoru_api.core.metrics import MetricsRegistry
from yoru_api.modules.ops.domain import evaluate_launch_gates


def test_metrics_registry_renders_prometheus() -> None:
    registry = MetricsRegistry()
    registry.begin_request()
    registry.end_request("GET", "/health/live", 200, 12.5)

    output = registry.render_prometheus()

    assert "yoru_http_requests_total" in output
    assert 'route="/health/live"' in output
    assert 'status="200"' in output


def test_launch_gate_passes_with_recent_restore_drill() -> None:
    now = datetime(2026, 8, 2, tzinfo=UTC)
    status, checks = evaluate_launch_gates(
        app_env="production",
        docs_enabled=False,
        cookie_secure=True,
        database_ok=True,
        current_alembic_head="20260802_0010",
        expected_alembic_head="20260802_0010",
        open_critical_security_events=0,
        last_restore_drill_at=now - timedelta(days=3),
        restore_drill_max_age_days=30,
        now=now,
    )

    assert status == "pass"
    assert all(check["status"] == "pass" for check in checks)


def test_launch_gate_fails_for_stale_restore_and_security_event() -> None:
    now = datetime(2026, 8, 2, tzinfo=UTC)
    status, checks = evaluate_launch_gates(
        app_env="production",
        docs_enabled=False,
        cookie_secure=True,
        database_ok=True,
        current_alembic_head="20260802_0010",
        expected_alembic_head="20260802_0010",
        open_critical_security_events=1,
        last_restore_drill_at=now - timedelta(days=60),
        restore_drill_max_age_days=30,
        now=now,
    )

    assert status == "fail"
    failed = {check["code"] for check in checks if check["status"] == "fail"}
    assert failed == {"critical_security_events", "restore_drill"}


def test_local_environment_is_warning_not_failure() -> None:
    now = datetime(2026, 8, 2, tzinfo=UTC)
    status, checks = evaluate_launch_gates(
        app_env="local",
        docs_enabled=True,
        cookie_secure=False,
        database_ok=True,
        current_alembic_head="20260802_0010",
        expected_alembic_head="20260802_0010",
        open_critical_security_events=0,
        last_restore_drill_at=now,
        restore_drill_max_age_days=30,
        now=now,
    )

    assert status == "warn"
    assert not any(check["status"] == "fail" for check in checks)
