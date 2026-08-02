from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any


class MetricsRegistry:
    """Small in-process registry for baseline operational metrics.

    It intentionally avoids a new runtime dependency. Multi-replica production
    deployments should scrape each replica or replace this implementation with
    a shared/OpenTelemetry backend.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.time()
        self._in_flight = 0
        self._request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        self._duration_ms_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._duration_count: dict[tuple[str, str], int] = defaultdict(int)

    def begin_request(self) -> None:
        with self._lock:
            self._in_flight += 1

    def end_request(self, method: str, route: str, status_code: int, duration_ms: float) -> None:
        key = (method, route)
        with self._lock:
            self._in_flight = max(0, self._in_flight - 1)
            self._request_counts[(method, route, status_code)] += 1
            self._duration_ms_sum[key] += max(0.0, duration_ms)
            self._duration_count[key] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            request_counts = [
                {
                    "method": method,
                    "route": route,
                    "status_code": status,
                    "count": count,
                }
                for (method, route, status), count in sorted(self._request_counts.items())
            ]
            durations = []
            for (method, route), count in sorted(self._duration_count.items()):
                total = self._duration_ms_sum[(method, route)]
                durations.append(
                    {
                        "method": method,
                        "route": route,
                        "count": count,
                        "average_ms": round(total / count, 3) if count else 0.0,
                        "total_ms": round(total, 3),
                    }
                )
            return {
                "uptime_seconds": round(time.time() - self._started_at, 3),
                "in_flight": self._in_flight,
                "requests": request_counts,
                "durations": durations,
            }

    @staticmethod
    def _escape(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )

    def render_prometheus(self) -> str:
        snapshot = self.snapshot()
        lines = [
            "# HELP yoru_uptime_seconds Process uptime in seconds.",
            "# TYPE yoru_uptime_seconds gauge",
            f"yoru_uptime_seconds {snapshot['uptime_seconds']}",
            "# HELP yoru_http_requests_in_flight Current in-flight HTTP requests.",
            "# TYPE yoru_http_requests_in_flight gauge",
            f"yoru_http_requests_in_flight {snapshot['in_flight']}",
            "# HELP yoru_http_requests_total Total HTTP requests.",
            "# TYPE yoru_http_requests_total counter",
        ]
        for row in snapshot["requests"]:
            method = self._escape(str(row["method"]))
            route = self._escape(str(row["route"]))
            status = int(row["status_code"])
            lines.append(
                f'yoru_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {row["count"]}'
            )
        lines.extend(
            [
                "# HELP yoru_http_request_duration_ms_sum Sum of HTTP request duration in milliseconds.",
                "# TYPE yoru_http_request_duration_ms_sum counter",
            ]
        )
        for row in snapshot["durations"]:
            method = self._escape(str(row["method"]))
            route = self._escape(str(row["route"]))
            lines.append(
                f'yoru_http_request_duration_ms_sum{{method="{method}",route="{route}"}} {row["total_ms"]}'
            )
        lines.extend(
            [
                "# HELP yoru_http_request_duration_ms_count Count of measured HTTP requests.",
                "# TYPE yoru_http_request_duration_ms_count counter",
            ]
        )
        for row in snapshot["durations"]:
            method = self._escape(str(row["method"]))
            route = self._escape(str(row["route"]))
            lines.append(
                f'yoru_http_request_duration_ms_count{{method="{method}",route="{route}"}} {row["count"]}'
            )
        return "\n".join(lines) + "\n"