from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from yoru_api import __version__
from yoru_api.app_registry import configure_middleware, register_routers
from yoru_api.core.checks import DependencyHealthChecker
from yoru_api.core.database import create_database_engine, create_session_factory
from yoru_api.core.logging import configure_logging
from yoru_api.core.metrics import MetricsRegistry
from yoru_api.core.problem import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
)
from yoru_api.core.settings import Settings, get_settings
from yoru_api.modules.identity.rate_limit import LoginRateLimiter


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

    configure_middleware(app, app_settings, metrics_registry)
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

    register_routers(app, app_settings.api_v1_prefix)
    return app


app = create_app()
