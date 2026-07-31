from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from yoru_api.core.middleware import request_id_context


@dataclass(slots=True)
class AppError(Exception):
    status_code: int
    code: str
    title: str
    detail: str | None = None


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
    return JSONResponse(
        status_code=error.status_code,
        content=payload,
        media_type="application/problem+json",
    )
