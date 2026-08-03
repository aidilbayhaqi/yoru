from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from yoru_api.core.middleware import request_id_context


@dataclass(slots=True)
class AppError(Exception):
    status_code: int
    code: str
    title: str
    detail: str | None = None


def _problem_response(*, status_code: int, payload: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        media_type="application/problem+json",
        headers={"Cache-Control": "no-store"},
    )


async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    payload = {
        "type": f"https://docs.yoru.invalid/errors/{error.code.lower().replace('_', '-')}",
        "title": error.title,
        "status": error.status_code,
        "code": error.code,
        "detail": error.detail,
        "instance": request.url.path,
        "request_id": request_id_context.get(),
    }
    return _problem_response(status_code=error.status_code, payload=payload)


def _validation_field(location: tuple[str | int, ...]) -> str:
    ignored = {"body", "query", "path", "header", "cookie"}
    for item in reversed(location):
        if isinstance(item, str) and item not in ignored:
            return item
    return "_form"


def _validation_message(raw_message: object) -> str:
    message = str(raw_message or "Nilai tidak valid.").strip()
    prefix = "Value error, "
    if message.startswith(prefix):
        message = message[len(prefix) :]
    return message or "Nilai tidak valid."


async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    # Deliberately exclude Pydantic's `input` and `ctx` values. They can contain
    # passwords or non-JSON-safe exception objects.
    issues = []
    for item in error.errors():
        location = tuple(item.get("loc", ()))
        issues.append(
            {
                "field": _validation_field(location),
                "message": _validation_message(item.get("msg")),
                "code": str(item.get("type") or "value_error"),
                "location": list(location),
            }
        )

    payload = {
        "type": "https://docs.yoru.invalid/errors/request-validation-failed",
        "title": "Request validation failed",
        "status": 422,
        "code": "REQUEST_VALIDATION_FAILED",
        "detail": "One or more request fields are invalid.",
        "instance": request.url.path,
        "request_id": request_id_context.get(),
        "errors": issues,
    }
    return _problem_response(status_code=422, payload=payload)
