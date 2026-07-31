from fastapi.testclient import TestClient

from yoru_api.core.checks import CheckResult


def test_liveness_has_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "test-request-001"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["request_id"] == "test-request-001"
    assert response.headers["X-Request-ID"] == "test-request-001"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "<script>"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "<script>"


def test_readiness_returns_dependency_status(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert set(payload["dependencies"]) == {"postgres", "redis", "qdrant"}


def test_readiness_fails_closed_when_dependency_is_down(client: TestClient) -> None:
    class UnhealthyChecker:
        async def check_all(self) -> dict[str, CheckResult]:
            return {
                "postgres": CheckResult(status="ok", latency_ms=1),
                "redis": CheckResult(status="unavailable", latency_ms=2000),
                "qdrant": CheckResult(status="ok", latency_ms=1),
            }

    client.app.state.health_checker = UnhealthyChecker()
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
