import asyncio
import contextvars
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from yoru_api.core.metrics import MetricsRegistry

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="unknown"
)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
logger = logging.getLogger("yoru_api.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
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
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "route": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        finally:
            request_id_context.reset(token)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
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


class _RequestBodyTooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    @staticmethod
    def _problem(status_code: int, title: str, code: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "type": "about:blank",
                "title": title,
                "status": status_code,
                "code": code,
            },
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        content_lengths = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if len(content_lengths) > 1:
            response = self._problem(400, "Invalid Content-Length header", "INVALID_CONTENT_LENGTH")
            await response(scope, receive, send)
            return

        if content_lengths:
            try:
                content_length = int(content_lengths[0].decode("ascii"))
                if content_length < 0:
                    raise ValueError
            except (UnicodeDecodeError, ValueError):
                response = self._problem(
                    400,
                    "Invalid Content-Length header",
                    "INVALID_CONTENT_LENGTH",
                )
                await response(scope, receive, send)
                return
            if content_length > self._max_bytes:
                response = self._problem(
                    413,
                    "Request body too large",
                    "REQUEST_BODY_TOO_LARGE",
                )
                await response(scope, receive, send)
                return

        received_bytes = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._max_bytes:
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self._app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            response = self._problem(
                413,
                "Request body too large",
                "REQUEST_BODY_TOO_LARGE",
            )
            await response(scope, receive, send)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, timeout_seconds: float) -> None:
        super().__init__(app)
        self._timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await call_next(request)
        except TimeoutError:
            logger.warning(
                "request_timeout",
                extra={
                    "request_id": request_id_context.get(),
                    "method": request.method,
                    "route": request.url.path,
                    "timeout_seconds": self._timeout_seconds,
                },
            )
            return JSONResponse(
                status_code=504,
                content={
                    "type": "about:blank",
                    "title": "Request timed out",
                    "status": 504,
                    "code": "REQUEST_TIMEOUT",
                },
            )


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, registry: MetricsRegistry) -> None:
        super().__init__(app)
        self._registry = registry

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        self._registry.begin_request()
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "<unmatched>")
            duration_ms = (time.perf_counter() - started) * 1000
            self._registry.end_request(request.method, route_path, status_code, duration_ms)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    DOCS_PATHS = frozenset({"/docs", "/openapi.json", "/redoc"})

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

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

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
        else:
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(self)"
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")

        if request.url.path.startswith(self._auth_path_prefix):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        if self._production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains; preload",
            )
        if "server" in response.headers:
            del response.headers["server"]
        return response
