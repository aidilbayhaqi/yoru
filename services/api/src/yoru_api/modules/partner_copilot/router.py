from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.transport import validate_csrf_or_bearer
from yoru_api.modules.partner_copilot.repository import PartnerCopilotRepository
from yoru_api.modules.partner_copilot.schemas import DashboardResponse, FeedbackCreate, FeedbackResponse, InsightResponse, MessageCreate, MessageResponse, ScheduleResponse, ScheduleUpdate, SessionCreate, SessionDetail, SessionResponse, SnapshotRequest, SnapshotResponse, UsageSummary
from yoru_api.modules.partner_copilot.service import PartnerCopilotService

router = APIRouter(tags=["Partner Copilot"])

async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory): yield session

def get_service(request: Request, session: Annotated[AsyncSession, Depends(get_database_session)]) -> PartnerCopilotService:
    return PartnerCopilotService(PartnerCopilotRepository(session), request.app.state.settings)

Service = Annotated[PartnerCopilotService, Depends(get_service)]

def validate_csrf(request: Request) -> None:
    validate_csrf_or_bearer(request, csrf_cookie_name=CSRF_COOKIE)

def dashboard_payload(snapshot: object, insights: list[object]) -> DashboardResponse:
    return DashboardResponse(snapshot=SnapshotResponse.model_validate(snapshot), insights=[InsightResponse.model_validate(item) for item in insights])

@router.get("/copilot/dashboard", response_model=DashboardResponse)
async def dashboard(actor: CurrentActor, service: Service) -> DashboardResponse:
    snapshot, insights = await service.dashboard(actor); return dashboard_payload(snapshot, insights)

@router.post("/copilot/analyze", response_model=DashboardResponse)
async def analyze(payload: SnapshotRequest, request: Request, actor: CurrentActor, service: Service) -> DashboardResponse:
    validate_csrf(request); snapshot, insights = await service.analyze(actor, payload); return dashboard_payload(snapshot, insights)

@router.get("/copilot/insights", response_model=list[InsightResponse])
async def list_insights(actor: CurrentActor, service: Service, insight_status: str | None = Query(default="active", alias="status"), limit: int = Query(default=50, ge=1, le=100)) -> list[InsightResponse]:
    return [InsightResponse.model_validate(item) for item in await service.list_insights(actor, insight_status, limit)]

@router.post("/copilot/insights/{insight_id}/dismiss", response_model=InsightResponse)
async def dismiss_insight(insight_id: UUID, request: Request, actor: CurrentActor, service: Service) -> InsightResponse:
    validate_csrf(request); return InsightResponse.model_validate(await service.dismiss_insight(actor, insight_id))

@router.post("/copilot/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, request: Request, actor: CurrentActor, service: Service) -> SessionResponse:
    validate_csrf(request); return SessionResponse.model_validate(await service.create_session(actor, payload))

@router.get("/copilot/sessions", response_model=list[SessionResponse])
async def list_sessions(actor: CurrentActor, service: Service, limit: int = Query(default=50, ge=1, le=100)) -> list[SessionResponse]:
    return [SessionResponse.model_validate(item) for item in await service.list_sessions(actor, limit)]

@router.get("/copilot/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: UUID, actor: CurrentActor, service: Service) -> SessionDetail:
    item, messages = await service.session_detail(actor, session_id); payload = SessionResponse.model_validate(item).model_dump(); return SessionDetail(**payload, messages=[MessageResponse.model_validate(m) for m in messages])

@router.post("/copilot/sessions/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def chat(session_id: UUID, payload: MessageCreate, request: Request, actor: CurrentActor, service: Service) -> MessageResponse:
    validate_csrf(request); return MessageResponse.model_validate(await service.chat(actor, session_id, payload.question))

@router.post("/copilot/messages/{message_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def feedback(message_id: UUID, payload: FeedbackCreate, request: Request, actor: CurrentActor, service: Service) -> FeedbackResponse:
    validate_csrf(request); return FeedbackResponse.model_validate(await service.feedback(actor, message_id, payload))

@router.get("/copilot/digest", response_model=ScheduleResponse)
async def get_digest(actor: CurrentActor, service: Service) -> ScheduleResponse:
    return ScheduleResponse.model_validate(await service.schedule(actor))

@router.put("/copilot/digest", response_model=ScheduleResponse)
async def update_digest(payload: ScheduleUpdate, request: Request, actor: CurrentActor, service: Service) -> ScheduleResponse:
    validate_csrf(request); return ScheduleResponse.model_validate(await service.update_schedule(actor, payload))

@router.get("/copilot/usage", response_model=UsageSummary)
async def usage(actor: CurrentActor, service: Service) -> UsageSummary:
    calls, input_tokens, output_tokens, cost = await service.usage(actor); return UsageSummary(calls=calls, input_tokens=input_tokens, output_tokens=output_tokens, estimated_cost_minor=cost, currency="IDR")
