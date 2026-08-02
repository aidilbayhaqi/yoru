from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class GateCheck:
    code: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _is_recent(value: datetime | None, *, max_age_days: int, now: datetime) -> bool:
    if value is None:
        return False
    normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized >= now - timedelta(days=max_age_days)


def evaluate_launch_gates(
    *,
    app_env: str,
    docs_enabled: bool,
    cookie_secure: bool,
    database_ok: bool,
    current_alembic_head: str | None,
    expected_alembic_head: str,
    open_critical_security_events: int,
    last_restore_drill_at: datetime | None,
    restore_drill_max_age_days: int,
    now: datetime | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    current_time = now or datetime.now(UTC)
    checks: list[GateCheck] = []

    checks.append(
        GateCheck(
            "runtime_environment",
            "pass" if app_env in {"staging", "production"} else "warn",
            f"APP_ENV is {app_env}",
        )
    )
    checks.append(
        GateCheck(
            "api_docs",
            "pass" if not docs_enabled else ("fail" if app_env == "production" else "warn"),
            "Interactive API documentation is disabled" if not docs_enabled else "Interactive API documentation is enabled",
        )
    )
    checks.append(
        GateCheck(
            "secure_cookie",
            "pass" if cookie_secure else ("fail" if app_env == "production" else "warn"),
            "Session cookies are secure" if cookie_secure else "Session cookies are not marked secure",
        )
    )
    checks.append(
        GateCheck(
            "database_probe",
            "pass" if database_ok else "fail",
            "Database probe succeeded" if database_ok else "Database probe failed",
        )
    )
    migration_matches = current_alembic_head == expected_alembic_head
    checks.append(
        GateCheck(
            "migration_head",
            "pass" if migration_matches else "fail",
            f"Current Alembic head is {current_alembic_head or 'unknown'}; expected {expected_alembic_head}",
        )
    )
    checks.append(
        GateCheck(
            "critical_security_events",
            "pass" if open_critical_security_events == 0 else "fail",
            f"Open critical security events: {open_critical_security_events}",
        )
    )
    restore_recent = _is_recent(
        last_restore_drill_at,
        max_age_days=restore_drill_max_age_days,
        now=current_time,
    )
    checks.append(
        GateCheck(
            "restore_drill",
            "pass" if restore_recent else "fail",
            (
                f"Successful restore drill is within {restore_drill_max_age_days} days"
                if restore_recent
                else f"No successful restore drill within {restore_drill_max_age_days} days"
            ),
        )
    )

    statuses = {check.status for check in checks}
    overall = "fail" if "fail" in statuses else ("warn" if "warn" in statuses else "pass")
    return overall, [check.as_dict() for check in checks]
