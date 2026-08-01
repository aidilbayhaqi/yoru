import contextvars
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="unknown",
)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

logger = logging.getLogger("yoru_api.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:

        supplied_request_id = request.headers.get("X-Request-ID", "")

        request_id = (
            supplied_request_id
            if _REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid.uuid4())
        )

        token = request_id_context.set(request_id)

        started = time.perf_counter()

        try:
            response = await call_next(request)

        finally:
            duration_ms = round(
                (time.perf_counter() - started) * 1000,
                2,
            )
            request_id_context.reset(token)

        response.headers["X-Request-ID"] = request_id

        route = request.scope.get("route")

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route": getattr(route, "path", request.url.path),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    DOCS_PATHS = {
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    def __init__(
        self,
        app: ASGIApp,
        *,
        production: bool = False,
        auth_path_prefix: str = "/api/v1/auth",
    ) -> None:

        super().__init__(app)

        self._production = production
        self._auth_path_prefix = auth_path_prefix


    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:

        response = await call_next(request)


        # ================================
        # Swagger / OpenAPI CSP
        # ================================
        #
        # FastAPI Swagger UI membutuhkan:
        # - javascript
        # - css
        # - inline script
        # - CDN swagger-ui
        #

        if request.url.path in self.DOCS_PATHS:

            response.headers.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https://fastapi.tiangolo.com; "
                    "font-src 'self' https://cdn.jsdelivr.net; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'"
                ),
            )


        # ================================
        # Normal Application CSP
        # ================================
        else:

            response.headers.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'none'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'none'"
                ),
            )


        # ================================
        # Security Headers
        # ================================

        response.headers.setdefault(
            "X-Content-Type-Options",
            "nosniff",
        )

        response.headers.setdefault(
            "X-Frame-Options",
            "DENY",
        )

        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin",
        )


        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(self)",
        )


        response.headers.setdefault(
            "Cross-Origin-Opener-Policy",
            "same-origin",
        )


        # ================================
        # Authentication Endpoint
        # ================================

        if request.url.path.startswith(self._auth_path_prefix):

            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"


        # ================================
        # Production HTTPS
        # ================================

        if self._production:

            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )


        return response