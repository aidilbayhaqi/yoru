from fastapi.testclient import TestClient

from yoru_api.runtime_contract import (
    EXPECTED_ROUTER_NAMES,
    RUNTIME_CONTRACT_VERSION,
    RUNTIME_STAGE,
)


def test_meta_reports_current_runtime_capabilities(client: TestClient) -> None:
    # YORU_PRIORITY1_META_TEST_V5_3
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == RUNTIME_STAGE
    assert payload["runtime_contract_version"] == RUNTIME_CONTRACT_VERSION
    assert payload["business_modules_enabled"] is True
    assert tuple(payload["modules"]) == EXPECTED_ROUTER_NAMES
    assert payload["features"]["identity"] is True
    assert payload["features"]["mobile_identity"] is True


def test_cors_allows_known_storefront(client: TestClient) -> None:
    response = client.options(
        "/api/v1/meta",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
