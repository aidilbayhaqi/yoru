from fastapi import Request

from yoru_api.core.problem import AppError
from yoru_api.modules.identity.security import constant_time_equal


def bearer_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization is None:
        return None

    scheme, separator, credentials = authorization.partition(" ")
    token = credentials.strip()
    if scheme.casefold() != "bearer" or not separator or not token:
        raise AppError(
            401,
            "AUTHORIZATION_HEADER_INVALID",
            "Authorization header must use the Bearer scheme",
        )
    if len(token) > 512:
        raise AppError(
            401,
            "AUTHORIZATION_HEADER_INVALID",
            "Authorization bearer token is invalid",
        )
    return token


def access_token_from_request(
    request: Request,
    *,
    cookie_name: str,
) -> str | None:
    bearer_token = bearer_token_from_request(request)
    if bearer_token is not None:
        return bearer_token
    return request.cookies.get(cookie_name)


def validate_request_origin(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin is not None and origin not in request.app.state.settings.cors_allowed_origins:
        raise AppError(403, "ORIGIN_DENIED", "Request origin is not allowed")


def validate_csrf_or_bearer(
    request: Request,
    *,
    csrf_cookie_name: str,
) -> None:
    validate_request_origin(request)

    # Bearer credentials are explicitly attached by the native client and are
    # not ambient browser credentials, so CSRF validation is not applicable.
    if bearer_token_from_request(request) is not None:
        return

    cookie_token = request.cookies.get(csrf_cookie_name, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not constant_time_equal(
        cookie_token,
        header_token,
    ):
        raise AppError(403, "CSRF_VALIDATION_FAILED", "CSRF validation failed")
