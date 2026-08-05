from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.security import constant_time_equal
from yoru_api.modules.identity.transport import validate_csrf_or_bearer
from yoru_api.modules.ops.repository import OpsRepository
from yoru_api.modules.ops.schemas import (
    LaunchGateResponse,
    OpsJobResponse,
    ReadinessResponse,
    RestoreDrillCreate,
    RetentionRunResponse,
    SecurityEventCreate,
    SecurityEventResolve,
    SecurityEventResponse,
)
from yoru_api.modules.ops.service import OpsService

router = APIRouter(tags=["Operations & Production Hardening"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> OpsService:
    return OpsService(OpsRepository(session), request.app.state.settings)


Service = Annotated[OpsService, Depends(get_service)]


def validate_csrf(request: Request) -> None:
    validate_csrf_or_bearer(request, csrf_cookie_name=CSRF_COOKIE)

def validate_metrics_token(request: Request, authorization: str | None, x_ops_token: str | None) -> None:
    settings = request.app.state.settings
    if not settings.metrics_enabled:
        raise AppError(404, "METRICS_DISABLED", "Metrics endpoint is disabled")
    configured = settings.metrics_token.get_secret_value() if settings.metrics_token else ""
    supplied = x_ops_token or ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization.removeprefix("Bearer ").strip()
    if not configured or not supplied or not constant_time_equal(configured, supplied):
        raise AppError(401, "METRICS_TOKEN_INVALID", "Metrics token is invalid")


@router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
async def metrics(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_ops_token: Annotated[str | None, Header(alias="X-Ops-Token")] = None,
) -> PlainTextResponse:
    validate_metrics_token(request, authorization, x_ops_token)
    return PlainTextResponse(
        request.app.state.metrics_registry.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/platform/ops/readiness", response_model=ReadinessResponse)
async def readiness(actor: CurrentActor, service: Service) -> ReadinessResponse:
    return ReadinessResponse(**await service.readiness(actor))


@router.get("/platform/ops/jobs", response_model=list[OpsJobResponse])
async def list_jobs(
    actor: CurrentActor,
    service: Service,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[OpsJobResponse]:
    return [OpsJobResponse.model_validate(item) for item in await service.list_jobs(actor, limit)]


@router.post(
    "/platform/ops/retention/run",
    response_model=RetentionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_retention(
    request: Request,
    actor: CurrentActor,
    service: Service,
) -> RetentionRunResponse:
    validate_csrf(request)
    job, results = await service.run_retention(actor)
    return RetentionRunResponse(job=OpsJobResponse.model_validate(job), results=results)


@router.post(
    "/platform/ops/restore-drills",
    response_model=OpsJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_restore_drill(
    payload: RestoreDrillCreate,
    request: Request,
    actor: CurrentActor,
    service: Service,
) -> OpsJobResponse:
    validate_csrf(request)
    return OpsJobResponse.model_validate(await service.record_restore_drill(actor, payload))


@router.post(
    "/platform/ops/security-events",
    response_model=SecurityEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_security_event(
    payload: SecurityEventCreate,
    request: Request,
    actor: CurrentActor,
    service: Service,
) -> SecurityEventResponse:
    validate_csrf(request)
    return SecurityEventResponse.model_validate(
        await service.create_security_event(actor, payload)
    )


@router.get("/platform/ops/security-events", response_model=list[SecurityEventResponse])
async def list_security_events(
    actor: CurrentActor,
    service: Service,
    event_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SecurityEventResponse]:
    return [
        SecurityEventResponse.model_validate(item)
        for item in await service.list_security_events(actor, event_status, limit)
    ]


@router.post(
    "/platform/ops/security-events/{event_id}/resolve",
    response_model=SecurityEventResponse,
)
async def resolve_security_event(
    event_id: UUID,
    payload: SecurityEventResolve,
    request: Request,
    actor: CurrentActor,
    service: Service,
) -> SecurityEventResponse:
    validate_csrf(request)
    return SecurityEventResponse.model_validate(
        await service.resolve_security_event(actor, event_id, payload)
    )


@router.post(
    "/platform/ops/launch-gates/evaluate",
    response_model=LaunchGateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_launch_gate(
    request: Request,
    actor: CurrentActor,
    service: Service,
) -> LaunchGateResponse:
    validate_csrf(request)
    return LaunchGateResponse.model_validate(await service.evaluate_launch_gate(actor))


@router.get("/platform/ops/launch-gates/latest", response_model=LaunchGateResponse)
async def latest_launch_gate(actor: CurrentActor, service: Service) -> LaunchGateResponse:
    return LaunchGateResponse.model_validate(await service.latest_launch_gate(actor))
