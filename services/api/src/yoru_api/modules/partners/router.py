from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.transport import validate_csrf_or_bearer
from yoru_api.modules.partners.repository import PartnerBundle, PartnerRepository
from yoru_api.modules.partners.schemas import (
    BlockPartnerRequest,
    CreatePartnerRequest,
    CreateServiceAreaRequest,
    DocumentResponse,
    PartnerListResponse,
    PartnerResponse,
    RegisterDocumentRequest,
    ReviewDecisionRequest,
    ScanResultRequest,
    ServiceAreaResponse,
    UpdatePartnerRequest,
    VerificationResponse,
)
from yoru_api.modules.partners.service import PartnerService

router = APIRouter(tags=["Partner onboarding"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_partner_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PartnerService:
    return PartnerService(PartnerRepository(session))


PartnerServiceDependency = Annotated[PartnerService, Depends(get_partner_service)]


def _validate_csrf(request: Request) -> None:
    validate_csrf_or_bearer(request, csrf_cookie_name=CSRF_COOKIE)

def _to_response(bundle: PartnerBundle) -> PartnerResponse:
    partner = bundle.partner
    return PartnerResponse(
        id=partner.id,
        display_name=partner.display_name,
        legal_name=partner.legal_name,
        partner_type=partner.partner_type,
        contact_email=partner.contact_email,
        contact_phone=partner.contact_phone,
        address_line=partner.address_line,
        city=partner.city,
        province=partner.province,
        postal_code=partner.postal_code,
        description=partner.description,
        status=partner.status,
        submitted_at=partner.submitted_at,
        reviewed_at=partner.reviewed_at,
        review_reason=partner.review_reason,
        created_at=partner.created_at,
        updated_at=partner.updated_at,
        verification=VerificationResponse.model_validate(bundle.verification),
        documents=[DocumentResponse.model_validate(item) for item in bundle.documents],
        service_areas=[
            ServiceAreaResponse.model_validate(item) for item in bundle.service_areas
        ],
    )


@router.post(
    "/partners",
    response_model=PartnerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner(
    payload: CreatePartnerRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(await service.create_partner(actor=actor, payload=payload))


@router.get("/partners/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: UUID,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    return _to_response(await service.get_partner(actor=actor, partner_id=partner_id))


@router.patch("/partners/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: UUID,
    payload: UpdatePartnerRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(
        await service.update_partner(
            actor=actor,
            partner_id=partner_id,
            payload=payload,
        )
    )


@router.post(
    "/partners/{partner_id}/service-areas",
    response_model=ServiceAreaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_service_area(
    partner_id: UUID,
    payload: CreateServiceAreaRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> ServiceAreaResponse:
    _validate_csrf(request)
    item = await service.add_service_area(
        actor=actor,
        partner_id=partner_id,
        payload=payload,
    )
    return ServiceAreaResponse.model_validate(item)


@router.delete(
    "/partners/{partner_id}/service-areas/{service_area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service_area(
    partner_id: UUID,
    service_area_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> Response:
    _validate_csrf(request)
    await service.delete_service_area(
        actor=actor,
        partner_id=partner_id,
        service_area_id=service_area_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/partners/{partner_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_document(
    partner_id: UUID,
    payload: RegisterDocumentRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> DocumentResponse:
    _validate_csrf(request)
    item = await service.register_document(
        actor=actor,
        partner_id=partner_id,
        payload=payload,
    )
    return DocumentResponse.model_validate(item)


@router.post("/partners/{partner_id}/submit", response_model=PartnerResponse)
async def submit_partner(
    partner_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(await service.submit(actor=actor, partner_id=partner_id))


@router.get("/admin/partners", response_model=PartnerListResponse)
async def list_partner_applications(
    actor: CurrentActor,
    service: PartnerServiceDependency,
    application_status: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=50, ge=1, le=100),
) -> PartnerListResponse:
    bundles = await service.list_for_review(
        actor=actor,
        status=application_status,
        limit=limit,
    )
    return PartnerListResponse(data=[_to_response(bundle) for bundle in bundles])


@router.post(
    "/admin/partner-documents/{document_id}/scan-result",
    response_model=DocumentResponse,
)
async def record_document_scan_result(
    document_id: UUID,
    payload: ScanResultRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> DocumentResponse:
    _validate_csrf(request)
    document = await service.mark_scan_result(
        actor=actor,
        document_id=document_id,
        payload=payload,
    )
    return DocumentResponse.model_validate(document)


@router.post("/admin/partners/{partner_id}/review/start", response_model=PartnerResponse)
async def start_partner_review(
    partner_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(await service.start_review(actor=actor, partner_id=partner_id))


@router.post("/admin/partners/{partner_id}/verify", response_model=PartnerResponse)
async def decide_partner_review(
    partner_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(
        await service.decide_review(
            actor=actor,
            partner_id=partner_id,
            payload=payload,
        )
    )


@router.post("/admin/partners/{partner_id}/block", response_model=PartnerResponse)
async def block_partner(
    partner_id: UUID,
    payload: BlockPartnerRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(
        await service.block(actor=actor, partner_id=partner_id, reason=payload.reason)
    )


@router.post("/admin/partners/{partner_id}/reinstate", response_model=PartnerResponse)
async def reinstate_partner(
    partner_id: UUID,
    payload: BlockPartnerRequest,
    request: Request,
    actor: CurrentActor,
    service: PartnerServiceDependency,
) -> PartnerResponse:
    _validate_csrf(request)
    return _to_response(
        await service.reinstate(actor=actor, partner_id=partner_id, reason=payload.reason)
    )
