from fastapi.testclient import TestClient


def test_meta_is_explicit_about_disabled_business_features(client: TestClient) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "identity-foundation"
    assert payload["business_modules_enabled"] is False
    assert payload["features"]["identity"] is True
    assert payload["features"]["customer_ai"] is False
    assert payload["features"]["partner_copilot"] is False


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
