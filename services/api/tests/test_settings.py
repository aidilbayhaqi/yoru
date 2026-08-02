import secrets

import pytest
from pydantic import ValidationError

from yoru_api.core.settings import Settings


def test_wildcard_cors_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS"):
        Settings(cors_allowed_origins="*", _env_file=None)


def test_production_placeholder_secrets_are_rejected() -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        Settings(
            app_env="production",
            cors_allowed_origins="https://yoru.test",
            cookie_secure=True,
            _env_file=None,
        )


def test_csv_configuration_is_normalized() -> None:
    settings = Settings(
        cors_allowed_origins=(
            "https://store.yoru.test,https://console.yoru.test"
        ),
        trusted_hosts="api.yoru.test,localhost",
        _env_file=None,
    )

    assert settings.cors_allowed_origins == (
        "https://store.yoru.test",
        "https://console.yoru.test",
    )
    assert settings.trusted_hosts == ("api.yoru.test", "localhost")


def test_csv_configuration_is_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://store.yoru.test,https://console.yoru.test",
    )
    monkeypatch.setenv("TRUSTED_HOSTS", "api.yoru.test,localhost")

    settings = Settings(_env_file=None)

    assert settings.cors_allowed_origins == (
        "https://store.yoru.test",
        "https://console.yoru.test",
    )
    assert settings.trusted_hosts == ("api.yoru.test", "localhost")


def production_values() -> dict[str, object]:
    return {
        "app_env": "production",
        "cors_allowed_origins": "https://store.yoru.test,https://console.yoru.test",
        "trusted_hosts": "api.yoru.test",
        "database_url": "postgresql+asyncpg://yoru:strong-password@postgres:5432/yoru",
        "session_signing_key": secrets.token_urlsafe(48),
        "refresh_token_pepper": secrets.token_urlsafe(48),
        "payment_webhook_secret": secrets.token_urlsafe(48),
        "metrics_token": secrets.token_urlsafe(48),
        "cookie_secure": True,
        "_env_file": None,
    }


def test_production_insecure_cookie_is_rejected() -> None:
    values = production_values()
    values["cookie_secure"] = False
    with pytest.raises(ValidationError, match="cookies must be secure"):
        Settings(**values)


def test_production_local_trusted_host_is_rejected() -> None:
    values = production_values()
    values["trusted_hosts"] = "api.yoru.test,localhost"
    with pytest.raises(ValidationError, match="trusted hosts"):
        Settings(**values)


def test_production_metrics_requires_strong_token() -> None:
    values = production_values()
    values["metrics_token"] = "short"
    with pytest.raises(ValidationError, match="metrics token"):
        Settings(**values)


def test_production_configuration_disables_docs() -> None:
    settings = Settings(**production_values())
    assert settings.docs_enabled is False
