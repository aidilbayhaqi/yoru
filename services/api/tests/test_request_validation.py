from fastapi.testclient import TestClient

from yoru_api.modules.identity.schemas import RegisterRequest


def test_register_request_normalizes_email_and_name() -> None:
    payload = RegisterRequest(
        email="  CUSTOMER@Example.COM ",
        full_name="  Aidil    Bayhaqi  ",
        password="StrongPassword!2026",
    )

    assert str(payload.email) == "customer@example.com"
    assert payload.full_name == "Aidil Bayhaqi"


def test_register_request_rejects_password_boundary_whitespace() -> None:
    try:
        RegisterRequest(
            email="customer@example.com",
            full_name="Aidil Bayhaqi",
            password=" StrongPassword!2026",
        )
    except ValueError as error:
        assert "must not start or end with whitespace" in str(error)
    else:
        raise AssertionError("password whitespace should have been rejected")


def test_register_422_uses_stable_problem_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "not-an-email",
            "full_name": " ",
            "password": "weak",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "REQUEST_VALIDATION_FAILED"
    assert payload["status"] == 422
    assert payload["request_id"]
    assert payload["detail"] == "One or more request fields are invalid."
    fields = {item["field"] for item in payload["errors"]}
    assert {"email", "full_name", "password"}.issubset(fields)

    # Validation responses must never echo submitted values such as passwords.
    serialized = response.text
    assert "weak" not in serialized
    assert response.headers["cache-control"] == "no-store"


def test_register_422_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "customer@example.com",
            "full_name": "Aidil Bayhaqi",
            "password": "StrongPassword!2026",
            "role": "super_admin",
        },
    )

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert any(item["field"] == "role" and item["code"] == "extra_forbidden" for item in errors)
