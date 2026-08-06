from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from yoru_api.core.problem import AppError
from yoru_api.modules.identity.permissions import Actor

from yoru_api.modules.identity.rate_limit import LoginRateLimiter
from yoru_api.modules.identity.router import (
    IdentityServiceDependency,
    _request_ip_prefix,
    _session_response,
)
from yoru_api.modules.identity.schemas import (
    LoginRequest,
    MessageResponse,
    MobileRefreshRequest,
    MobileTokenResponse,
    RegisterRequest,
    SessionResponse,
)
from yoru_api.modules.identity.security import TokenPair
from yoru_api.modules.identity.transport import (
    bearer_token_from_request,
    validate_request_origin,
)

router = APIRouter(prefix="/mobile/auth", tags=["Mobile Authentication"])

# YORU_PRIORITY3_MOBILE_BEARER_AUTH_V1
async def get_current_mobile_actor(
    request: Request,
    service: IdentityServiceDependency,
) -> Actor:
    token = bearer_token_from_request(request)
    if token is None:
        raise AppError(
            401,
            "AUTHENTICATION_REQUIRED",
            "Mobile endpoints require a Bearer access token",
        )
    return await service.authenticate_access(token)


MobileActor = Annotated[Actor, Depends(get_current_mobile_actor)]


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _token_response(
    *,
    actor: Actor,
    tokens: TokenPair,
    request: Request,
) -> MobileTokenResponse:
    settings = request.app.state.settings
    return MobileTokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
        session=_session_response(actor),
    )


@router.post(
    "/register",
    response_model=MobileTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_customer(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> MobileTokenResponse:
    validate_request_origin(request)
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
    _disable_caching(response)
    return _token_response(
        actor=result.actor,
        tokens=result.tokens,
        request=request,
    )


@router.post("/login", response_model=MobileTokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> MobileTokenResponse:
    validate_request_origin(request)
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
    _disable_caching(response)
    return _token_response(
        actor=result.actor,
        tokens=result.tokens,
        request=request,
    )


@router.post("/refresh", response_model=MobileTokenResponse)
async def refresh(
    payload: MobileRefreshRequest,
    request: Request,
    response: Response,
    service: IdentityServiceDependency,
) -> MobileTokenResponse:
    validate_request_origin(request)
    actor, tokens = await service.refresh(refresh_token=payload.refresh_token)
    _disable_caching(response)
    return _token_response(actor=actor, tokens=tokens, request=request)


@router.get("/me", response_model=SessionResponse)
async def me(actor: MobileActor, response: Response) -> SessionResponse:
    _disable_caching(response)
    return _session_response(actor)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    actor: MobileActor,
    response: Response,
    service: IdentityServiceDependency,
) -> MessageResponse:
    await service.logout(actor=actor)
    _disable_caching(response)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    actor: MobileActor,
    response: Response,
    service: IdentityServiceDependency,
) -> MessageResponse:
    await service.logout_all(actor=actor)
    _disable_caching(response)
    return MessageResponse(message="All sessions revoked")
