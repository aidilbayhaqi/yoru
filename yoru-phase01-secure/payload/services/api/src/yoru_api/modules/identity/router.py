import ipaddress
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from yoru_api.core.database import session_scope
from yoru_api.core.problem import AppError
from yoru_api.core.settings import Settings
from yoru_api.modules.identity.permissions import Actor
from yoru_api.modules.identity.rate_limit import LoginRateLimiter
from yoru_api.modules.identity.repository import IdentityRepository
from yoru_api.modules.identity.schemas import (
    LoginRequest,
    MembershipResponse,
    MessageResponse,
    RegisterRequest,
    SelectPartnerRequest,
    SessionListItem,
    SessionResponse,
    UserResponse,
)
from yoru_api.modules.identity.security import TokenPair, constant_time_equal
from yoru_api.modules.identity.service import IdentityService

router = APIRouter(prefix="/auth", tags=["Authentication"])

ACCESS_COOKIE = "yoru_access"
REFRESH_COOKIE = "yoru_refresh"
CSRF_COOKIE = "yoru_csrf"


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in session_scope(request.app.state.session_factory):
        yield session


def get_identity_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IdentityService:
    return IdentityService(IdentityRepository(session), request.app.state.settings)


def _request_ip_prefix(request: Request) -> str | None:
    if request.client is None:
        return None
    try:
        address = ipaddress.ip_address(request.client.host)
    except ValueError:
        return None
    prefix = 24 if address.version == 4 else 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


def _validate_origin(request: Request) -> None:
    origin = request.headers.get("Origin")
    if origin is not None and origin not in request.app.state.settings.cors_allowed_origins:
        raise AppError(403, "ORIGIN_DENIED", "Request origin is not allowed")


def _validate_csrf(request: Request) -> None:
    _validate_origin(request)
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not constant_time_equal(
        cookie_token, header_token
    ):
        raise AppError(403, "CSRF_VALIDATION_FAILED", "CSRF validation failed")


async def get_current_actor(
    request: Request,
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> Actor:
    return await service.authenticate_access(request.cookies.get(ACCESS_COOKIE))


CurrentActor = Annotated[Actor, Depends(get_current_actor)]
IdentityServiceDependency = Annotated[IdentityService, Depends(get_identity_service)]


def _session_response(actor: Actor) -> SessionResponse:
    return SessionResponse(
        user=UserResponse(
            id=actor.user_id,
            email=actor.email,
            full_name=actor.full_name,
            status=actor.status,
        ),
        active_partner_id=actor.active_partner_id,
        platform_roles=sorted(actor.platform_roles),
        permissions=sorted(actor.permissions),
        memberships=[
            MembershipResponse(
                partner_id=membership.partner_id,
                partner_status=membership.partner_status,
                membership_status=membership.membership_status,
                role=membership.role,
                permissions=sorted(membership.permissions),
            )
            for membership in actor.memberships
        ],
    )


def _set_session_cookies(
    response: Response,
    *,
    tokens: TokenPair,
    settings: Settings,
) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        tokens.access_token,
        max_age=settings.access_token_ttl_seconds,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.refresh_token_ttl_seconds,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/api/v1/auth",
    )
    response.set_cookie(
        CSRF_COOKIE,
        tokens.csrf_token,
        max_age=settings.refresh_token_ttl_seconds,
        secure=settings.cookie_secure,
        httponly=False,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def _clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        ACCESS_COOKIE, domain=settings.cookie_domain, path="/"
    )
    response.delete_cookie(
        REFRESH_COOKIE,
        domain=settings.cookie_domain,
        path="/api/v1/auth",
    )
    response.delete_cookie(CSRF_COOKIE, domain=settings.cookie_domain, path="/")
    response.headers["Cache-Control"] = "no-store"


@router.post(
    "/register",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_customer(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> SessionResponse:
    _validate_origin(request)
    limiter: LoginRateLimiter = request.app.state.login_rate_limiter
    ip_address = request.client.host if request.client else "unknown"
    await limiter.check(ip_address=ip_address, email=str(payload.email))
    result = await service.register_customer(
        email=str(payload.email),
        full_name=payload.full_name,
        password=payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip_prefix=_request_ip_prefix(request),
    )
    await limiter.clear(ip_address=ip_address, email=str(payload.email))
    _set_session_cookies(
        response, tokens=result.tokens, settings=request.app.state.settings
    )
    return _session_response(result.actor)


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> SessionResponse:
    _validate_origin(request)
    limiter: LoginRateLimiter = request.app.state.login_rate_limiter
    ip_address = request.client.host if request.client else "unknown"
    await limiter.check(ip_address=ip_address, email=str(payload.email))
    result = await service.login(
        email=str(payload.email),
        password=payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip_prefix=_request_ip_prefix(request),
    )
    await limiter.clear(ip_address=ip_address, email=str(payload.email))
    _set_session_cookies(
        response, tokens=result.tokens, settings=request.app.state.settings
    )
    return _session_response(result.actor)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> SessionResponse:
    _validate_csrf(request)
    actor, tokens = await service.refresh(
        refresh_token=request.cookies.get(REFRESH_COOKIE)
    )
    _set_session_cookies(
        response,
        tokens=tokens,
        settings=request.app.state.settings,
    )
    return _session_response(actor)


@router.get("/me", response_model=SessionResponse)
async def me(actor: CurrentActor) -> SessionResponse:
    return _session_response(actor)


@router.patch("/active-partner", response_model=SessionResponse)
async def select_active_partner(
    payload: SelectPartnerRequest,
    request: Request,
    actor: CurrentActor,
    service: IdentityServiceDependency,
) -> SessionResponse:
    _validate_csrf(request)
    access_token = request.cookies.get(ACCESS_COOKIE)
    if access_token is None:
        raise AppError(401, "AUTHENTICATION_REQUIRED", "Authentication required")
    refreshed_actor = await service.select_partner(
        actor=actor,
        partner_id=payload.partner_id,
        access_token=access_token,
    )
    return _session_response(refreshed_actor)


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    actor: CurrentActor,
    service: IdentityServiceDependency,
) -> list[SessionListItem]:
    sessions = await service.list_sessions(actor)
    return [
        SessionListItem(
            id=item.id,
            active_partner_id=item.active_partner_id,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            current=item.id == actor.session_id,
        )
        for item in sessions
    ]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    request: Request,
    response: Response,
    actor: CurrentActor,
    service: IdentityServiceDependency,
) -> MessageResponse:
    _validate_csrf(request)
    await service.revoke_session(actor=actor, session_id=session_id)
    if session_id == actor.session_id:
        _clear_session_cookies(response, request.app.state.settings)
    return MessageResponse(message="Session revoked")


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    actor: CurrentActor,
    service: IdentityServiceDependency,
) -> MessageResponse:
    _validate_csrf(request)
    await service.logout(actor=actor)
    _clear_session_cookies(response, request.app.state.settings)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    request: Request,
    response: Response,
    actor: CurrentActor,
    service: IdentityServiceDependency,
) -> MessageResponse:
    _validate_csrf(request)
    await service.logout_all(actor=actor)
    _clear_session_cookies(response, request.app.state.settings)
    return MessageResponse(message="All sessions revoked")
