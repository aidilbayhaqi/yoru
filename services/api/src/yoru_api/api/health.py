from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from yoru_api import __version__
from yoru_api.core.middleware import request_id_context

router = APIRouter(prefix="/health", tags=["health"])


def _base_payload(request: Request, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "service": request.app.title,
        "version": __version__,
        "request_id": request_id_context.get(),
    }


@router.get("/live")
async def liveness(request: Request) -> dict[str, Any]:
    return _base_payload(request, "ok")


@router.get("/startup")
async def startup(request: Request) -> JSONResponse:
    started = bool(getattr(request.app.state, "started", False))
    payload = _base_payload(request, "ok" if started else "unavailable")
    return JSONResponse(payload, status_code=200 if started else 503)


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    checks = await request.app.state.health_checker.check_all()
    ready = all(check.status == "ok" for check in checks.values())
    payload = _base_payload(request, "ok" if ready else "unavailable")
    payload["dependencies"] = {
        name: {"status": result.status, "latency_ms": result.latency_ms}
        for name, result in checks.items()
    }
    return JSONResponse(payload, status_code=200 if ready else 503)
