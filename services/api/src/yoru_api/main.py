from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from yoru_api import __version__
from yoru_api.api.health import router as health_router
from yoru_api.api.meta import router as meta_router
from yoru_api.core.checks import DependencyHealthChecker
from yoru_api.core.database import create_database_engine, create_session_factory
from yoru_api.core.logging import configure_logging
from yoru_api.core.metrics import MetricsRegistry
from yoru_api.core.middleware import (
    MetricsMiddleware,
    RequestContextMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
    SecurityHeadersMiddleware,
)
from yoru_api.core.problem import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
)
from yoru_api.core.settings import Settings, get_settings
from yoru_api.modules.advisor.router import router as advisor_router
from yoru_api.modules.bookings.router import router as bookings_router
from yoru_api.modules.catalog.router import router as catalog_router
from yoru_api.modules.commerce.router import router as commerce_router
from yoru_api.modules.finance.router import router as finance_router
from yoru_api.modules.identity.rate_limit import LoginRateLimiter
from yoru_api.modules.identity.router import router as identity_router
from yoru_api.modules.ops.router import router as ops_router
from yoru_api.modules.partner_copilot.router import router as partner_copilot_router
from yoru_api.modules.partners.router import router as partners_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)
    engine = create_database_engine(app_settings)
    session_factory = create_session_factory(engine)
    login_rate_limiter = LoginRateLimiter(app_settings)
    metrics_registry = MetricsRegistry()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.started = True
        yield
        app.state.started = False
        await login_rate_limiter.close()
        await engine.dispose()

    app = FastAPI(
        title="Yoru API",
        version=__version__,
        docs_url="/docs" if app_settings.docs_enabled else None,
        redoc_url="/redoc" if app_settings.docs_enabled else None,
        openapi_url="/openapi.json" if app_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.login_rate_limiter = login_rate_limiter
    app.state.health_checker = DependencyHealthChecker(app_settings, engine)
    app.state.metrics_registry = metrics_registry
    app.state.started = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-CSRF-Token",
            "X-Ops-Token",
            "X-Request-ID",
            "X-Yoru-Signature",
        ],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(app_settings.trusted_hosts),
    )
    app.add_middleware(
        SecurityHeadersMiddleware,
        production=app_settings.app_env == "production",
        auth_path_prefix=f"{app_settings.api_v1_prefix}/auth",
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=app_settings.max_request_body_bytes,
    )
    app.add_middleware(
        RequestTimeoutMiddleware,
        timeout_seconds=app_settings.request_timeout_seconds,
    )
    app.add_middleware(MetricsMiddleware, registry=metrics_registry)
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,  # type: ignore[arg-type]
    )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "Yoru API",
            "version": __version__,
            "stage": "phase-9-pre-production",
            "release_id": app_settings.release_id,
        }

    app.include_router(health_router)
    app.include_router(meta_router, prefix=app_settings.api_v1_prefix)
    app.include_router(identity_router, prefix=app_settings.api_v1_prefix)
    app.include_router(partners_router, prefix=app_settings.api_v1_prefix)
    app.include_router(catalog_router, prefix=app_settings.api_v1_prefix)
    app.include_router(commerce_router, prefix=app_settings.api_v1_prefix)
    app.include_router(bookings_router, prefix=app_settings.api_v1_prefix)
    app.include_router(finance_router, prefix=app_settings.api_v1_prefix)
    app.include_router(advisor_router, prefix=app_settings.api_v1_prefix)
    app.include_router(partner_copilot_router, prefix=app_settings.api_v1_prefix)
    app.include_router(ops_router, prefix=app_settings.api_v1_prefix)
    return app


app = create_app()
