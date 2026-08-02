from collections.abc import AsyncIterator
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.modules.bookings.repository import BookingBundle, BookingRepository
from yoru_api.modules.bookings.schemas import (
    BookingAssignRequest,
    BookingAssignmentResponse,
    BookingCompleteRequest,
    BookingCreateRequest,
    BookingListResponse,
    BookingReasonRequest,
    BookingResponse,
    CustomerAddressCreate,
    CustomerAddressResponse,
    MessageResponse,
    TrackingConsentRequest,
    TrackingSessionResponse,
    TrackingPingRequest,
    TrackingPingResponse,
    VerificationIssueResponse,
    VerificationRequest,
)
from yoru_api.modules.bookings.service import BookingService
from yoru_api.modules.identity.router import CSRF_COOKIE, CurrentActor
from yoru_api.modules.identity.security import constant_time_equal

router = APIRouter(tags=["Booking and home-service operations"])


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_booking_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> BookingService:
    settings = request.app.state.settings
    return BookingService(
        BookingRepository(session),
        otp_secret=settings.session_signing_key.get_secret_value(),
        live_tracking_enabled=settings.feature_live_tracking,
    )


BookingServiceDependency = Annotated[BookingService, Depends(get_booking_service)]


def _validate_csrf(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin is not None and origin not in request.app.state.settings.cors_allowed_origins:
        raise AppError(403, "ORIGIN_DENIED", "Request origin is not allowed")
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not constant_time_equal(cookie_token, header_token):
        raise AppError(403, "CSRF_VALIDATION_FAILED", "CSRF validation failed")


def _response(bundle: BookingBundle) -> BookingResponse:
    return BookingResponse(
        **{
            field: getattr(bundle.booking, field)
            for field in BookingResponse.model_fields
            if field not in {"assignment", "tracking", "latest_location"}
        },
        assignment=(
            BookingAssignmentResponse.model_validate(bundle.assignment)
            if bundle.assignment is not None
            else None
        ),
        tracking=(
            TrackingSessionResponse.model_validate(bundle.tracking)
            if bundle.tracking is not None
            else None
        ),
        latest_location=(
            TrackingPingResponse.model_validate(bundle.latest_ping)
            if bundle.latest_ping is not None
            else None
        ),
    )


@router.post(
    "/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_address(
    payload: CustomerAddressCreate,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> CustomerAddressResponse:
    _validate_csrf(request)
    return CustomerAddressResponse.model_validate(
        await service.create_address(actor=actor, payload=payload)
    )


@router.get("/addresses", response_model=list[CustomerAddressResponse])
async def list_addresses(
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> list[CustomerAddressResponse]:
    return [
        CustomerAddressResponse.model_validate(item)
        for item in await service.list_addresses(actor)
    ]


@router.post(
    "/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    payload: BookingCreateRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(await service.create_booking(actor=actor, payload=payload))


@router.get("/bookings", response_model=BookingListResponse)
async def list_bookings(
    actor: CurrentActor,
    service: BookingServiceDependency,
    limit: int = Query(default=50, ge=1, le=100),
) -> BookingListResponse:
    return BookingListResponse(
        data=[_response(item) for item in await service.list_bookings(actor=actor, limit=limit)]
    )


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    return _response(await service.get_booking(actor=actor, booking_id=booking_id))


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    payload: BookingReasonRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.cancel(actor=actor, booking_id=booking_id, reason=payload.reason)
    )


@router.post(
    "/bookings/{booking_id}/verification/{purpose}/issue",
    response_model=VerificationIssueResponse,
)
async def issue_verification(
    booking_id: UUID,
    purpose: Literal["check_in", "check_out"],
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> VerificationIssueResponse:
    _validate_csrf(request)
    otp, expires_at = await service.issue_verification(
        actor=actor,
        booking_id=booking_id,
        purpose=purpose,
    )
    return VerificationIssueResponse(
        booking_id=booking_id,
        purpose=purpose,
        otp=otp,
        expires_at=expires_at,
    )


@router.post("/provider/bookings/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(await service.confirm(actor=actor, booking_id=booking_id))


@router.post("/provider/bookings/{booking_id}/assign", response_model=BookingResponse)
async def assign_booking(
    booking_id: UUID,
    payload: BookingAssignRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.assign(
            actor=actor,
            booking_id=booking_id,
            professional_id=payload.professional_id,
            notes=payload.notes,
        )
    )


@router.post("/provider/bookings/{booking_id}/start-trip", response_model=BookingResponse)
async def start_trip(
    booking_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(await service.start_trip(actor=actor, booking_id=booking_id))


@router.post("/provider/bookings/{booking_id}/arrive", response_model=BookingResponse)
async def arrive(
    booking_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(await service.arrive(actor=actor, booking_id=booking_id))


@router.post("/provider/bookings/{booking_id}/start", response_model=BookingResponse)
async def start_service(
    booking_id: UUID,
    payload: VerificationRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.start_service(actor=actor, booking_id=booking_id, otp=payload.otp)
    )


@router.post("/provider/bookings/{booking_id}/complete", response_model=BookingResponse)
async def complete_service(
    booking_id: UUID,
    payload: BookingCompleteRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.complete(actor=actor, booking_id=booking_id, payload=payload)
    )


@router.post("/provider/bookings/{booking_id}/no-show", response_model=BookingResponse)
async def mark_no_show(
    booking_id: UUID,
    payload: BookingReasonRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.no_show(actor=actor, booking_id=booking_id, reason=payload.reason)
    )


@router.post("/bookings/{booking_id}/tracking/consent", response_model=BookingResponse)
async def consent_tracking(
    booking_id: UUID,
    payload: TrackingConsentRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(
        await service.consent_tracking(
            actor=actor,
            booking_id=booking_id,
            ttl_minutes=payload.ttl_minutes,
        )
    )


@router.post(
    "/provider/bookings/{booking_id}/tracking/pings",
    response_model=TrackingPingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_tracking_ping(
    booking_id: UUID,
    payload: TrackingPingRequest,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> TrackingPingResponse:
    _validate_csrf(request)
    return TrackingPingResponse.model_validate(
        await service.add_tracking_ping(
            actor=actor,
            booking_id=booking_id,
            payload=payload,
        )
    )


@router.get(
    "/bookings/{booking_id}/tracking/latest",
    response_model=TrackingPingResponse,
)
async def latest_tracking_location(
    booking_id: UUID,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> TrackingPingResponse:
    return TrackingPingResponse.model_validate(
        await service.latest_location(actor=actor, booking_id=booking_id)
    )


@router.post("/bookings/{booking_id}/tracking/stop", response_model=BookingResponse)
async def stop_tracking(
    booking_id: UUID,
    request: Request,
    actor: CurrentActor,
    service: BookingServiceDependency,
) -> BookingResponse:
    _validate_csrf(request)
    return _response(await service.stop_tracking(actor=actor, booking_id=booking_id))


@router.get("/bookings-meta", response_model=MessageResponse, include_in_schema=False)
async def booking_meta() -> MessageResponse:
    return MessageResponse(message="Yoru booking operations v0.6.0")
