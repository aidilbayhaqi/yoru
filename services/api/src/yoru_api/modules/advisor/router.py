from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.modules.advisor.repository import AdvisorRepository
from yoru_api.modules.advisor.schemas import (
    AdvisorSessionCreate,
    AdvisorSessionDetail,
    AdvisorSessionResponse,
    ConsentCreate,
    ConsentResponse,
    EvaluationCreate,
    EvaluationResponse,
    FeedbackCreate,
    FeedbackResponse,
    MediaRegister,
    MediaResponse,
    MediaScanResult,
    RecommendationResponse,
    RetentionPurgeResponse,
)
from yoru_api.modules.advisor.service import AdvisorService
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.transport import validate_csrf_or_bearer

router = APIRouter(tags=["Customer AI Advisor"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_advisor_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AdvisorService:
    return AdvisorService(AdvisorRepository(session), request.app.state.settings)


AdvisorServiceDependency = Annotated[AdvisorService, Depends(get_advisor_service)]


def validate_csrf(request: Request) -> None:
    validate_csrf_or_bearer(request, csrf_cookie_name=CSRF_COOKIE)

def detail_response(item: object, media: list[object], recommendations: list[object]):
    payload = AdvisorSessionResponse.model_validate(item).model_dump()
    return AdvisorSessionDetail(
        **payload,
        media=[MediaResponse.model_validate(asset) for asset in media],
        recommendations=[
            RecommendationResponse.model_validate(recommendation)
            for recommendation in recommendations
        ],
    )


@router.get("/ai/consent", response_model=ConsentResponse)
async def current_consent(
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> ConsentResponse:
    return ConsentResponse.model_validate(await service.current_consent(actor))


@router.post("/ai/consent", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def grant_consent(
    payload: ConsentCreate,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> ConsentResponse:
    validate_csrf(request)
    item = await service.grant_consent(
        actor,
        photo_processing=payload.photo_processing,
        personalization=payload.personalization,
        retention_days=payload.retention_days,
    )
    return ConsentResponse.model_validate(item)


@router.delete("/ai/consent", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_consent(
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> None:
    validate_csrf(request)
    await service.revoke_consent(actor)


@router.post(
    "/ai/advisor/sessions",
    response_model=AdvisorSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: AdvisorSessionCreate,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> AdvisorSessionResponse:
    validate_csrf(request)
    return AdvisorSessionResponse.model_validate(await service.create_session(actor, payload))


@router.get("/ai/advisor/sessions", response_model=list[AdvisorSessionResponse])
async def list_sessions(
    actor: CurrentActor,
    service: AdvisorServiceDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AdvisorSessionResponse]:
    items = await service.list_sessions(actor, limit)
    return [AdvisorSessionResponse.model_validate(item) for item in items]


@router.get("/ai/advisor/sessions/{session_id}", response_model=AdvisorSessionDetail)
async def get_session(
    session_id: UUID,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> AdvisorSessionDetail:
    item, media, recommendations = await service.session_detail(actor, session_id)
    return detail_response(item, media, recommendations)


@router.post(
    "/ai/advisor/sessions/{session_id}/media",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_media(
    session_id: UUID,
    payload: MediaRegister,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> MediaResponse:
    validate_csrf(request)
    return MediaResponse.model_validate(
        await service.register_media(actor, session_id, payload)
    )


@router.post(
    "/platform/ai/media/{media_id}/scan",
    response_model=MediaResponse,
)
async def record_media_scan(
    media_id: UUID,
    payload: MediaScanResult,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> MediaResponse:
    validate_csrf(request)
    return MediaResponse.model_validate(await service.record_scan(actor, media_id, payload))


@router.post(
    "/ai/advisor/sessions/{session_id}/analyze",
    response_model=AdvisorSessionDetail,
)
async def analyze_session(
    session_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> AdvisorSessionDetail:
    validate_csrf(request)
    item, _ = await service.analyze(actor, session_id)
    refreshed, media, recommendations = await service.session_detail(actor, item.id)
    return detail_response(refreshed, media, recommendations)


@router.post(
    "/ai/advisor/sessions/{session_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_feedback(
    session_id: UUID,
    payload: FeedbackCreate,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> FeedbackResponse:
    validate_csrf(request)
    return FeedbackResponse.model_validate(await service.feedback(actor, session_id, payload))


@router.post(
    "/platform/ai/evaluations",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    payload: EvaluationCreate,
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
) -> EvaluationResponse:
    validate_csrf(request)
    return EvaluationResponse.model_validate(await service.run_evaluation(actor, payload))


@router.get("/platform/ai/evaluations", response_model=list[EvaluationResponse])
async def list_evaluations(
    actor: CurrentActor,
    service: AdvisorServiceDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[EvaluationResponse]:
    items = await service.list_evaluations(actor, limit)
    return [EvaluationResponse.model_validate(item) for item in items]


@router.post("/platform/ai/retention/purge", response_model=RetentionPurgeResponse)
async def purge_retention(
    request: Request,
    actor: CurrentActor,
    service: AdvisorServiceDependency,
    limit: int = Query(default=100, ge=1, le=1000),
) -> RetentionPurgeResponse:
    validate_csrf(request)
    sessions_expired, media_deleted = await service.purge_expired(actor, limit)
    return RetentionPurgeResponse(
        sessions_expired=sessions_expired,
        media_deleted=media_deleted,
    )
