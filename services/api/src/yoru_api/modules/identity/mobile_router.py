from fastapi import APIRouter, Request, Response, status

from yoru_api.modules.identity.rate_limit import LoginRateLimiter
from yoru_api.modules.identity.router import (
    CurrentActor,
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
from yoru_api.modules.identity.transport import validate_request_origin

router = APIRouter(prefix="/mobile/auth", tags=["Mobile Authentication"])


def _disable_caching(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _token_response(
    *,
    actor: CurrentActor,
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
async def me(actor: CurrentActor, response: Response) -> SessionResponse:
    _disable_caching(response)
    return _session_response(actor)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    actor: CurrentActor,
    response: Response,
    service: IdentityServiceDependency,
) -> MessageResponse:
    await service.logout(actor=actor)
    _disable_caching(response)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    actor: CurrentActor,
    response: Response,
    service: IdentityServiceDependency,
) -> MessageResponse:
    await service.logout_all(actor=actor)
    _disable_caching(response)
    return MessageResponse(message="All sessions revoked")
