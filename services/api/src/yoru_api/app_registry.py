# YORU_PRIORITY1_RUNTIME_COMPOSITION_V3
from collections import Counter
from dataclasses import dataclass
from typing import Final

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from yoru_api.api.health import router as health_router
from yoru_api.api.meta import router as meta_router
from yoru_api.core.metrics import MetricsRegistry
from yoru_api.core.middleware import (
    MetricsMiddleware,
    RequestContextMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
    SecurityHeadersMiddleware,
)
from yoru_api.core.settings import Settings
from yoru_api.modules.advisor.router import router as advisor_router
from yoru_api.modules.bookings.router import router as bookings_router
from yoru_api.modules.catalog.router import router as catalog_router
from yoru_api.modules.commerce.router import router as commerce_router
from yoru_api.modules.finance.router import router as finance_router
from yoru_api.modules.identity.mobile_router import router as mobile_identity_router
from yoru_api.modules.identity.router import router as identity_router
from yoru_api.modules.ops.router import router as ops_router
from yoru_api.modules.partner_copilot.router import router as partner_copilot_router
from yoru_api.modules.partners.router import router as partners_router
from yoru_api.runtime_contract import validate_runtime_contract


@dataclass(frozen=True, slots=True)
class RouterMount:
    name: str
    router: APIRouter
    versioned: bool = True


@dataclass(frozen=True, slots=True, order=True)
class RouteManifestEntry:
    method: str
    path: str
    name: str


ROUTER_MOUNTS: Final[tuple[RouterMount, ...]] = (
    RouterMount("health", health_router, versioned=False),
    RouterMount("meta", meta_router, versioned=True),
    RouterMount("identity", identity_router, versioned=True),
    RouterMount("mobile_identity", mobile_identity_router, versioned=True),
    RouterMount("partners", partners_router, versioned=True),
    RouterMount("catalog", catalog_router, versioned=True),
    RouterMount("commerce", commerce_router, versioned=True),
    RouterMount("bookings", bookings_router, versioned=True),
    RouterMount("finance", finance_router, versioned=True),
    RouterMount("advisor", advisor_router, versioned=True),
    RouterMount("partner_copilot", partner_copilot_router, versioned=True),
    RouterMount("ops", ops_router, versioned=True),
)

# app.user_middleware and runtime request traversal use this effective order.
MIDDLEWARE_REQUEST_ORDER: Final[tuple[str, ...]] = (
    "request_context",
    "security_headers",
    "metrics",
    "cors",
    "request_timeout",
    "request_size_limit",
    "trusted_host",
)

MIDDLEWARE_CLASS_ORDER: Final[tuple[str, ...]] = (
    "RequestContextMiddleware",
    "SecurityHeadersMiddleware",
    "MetricsMiddleware",
    "CORSMiddleware",
    "RequestTimeoutMiddleware",
    "RequestSizeLimitMiddleware",
    "TrustedHostMiddleware",
)


def configure_middleware(
    app: FastAPI,
    settings: Settings,
    metrics_registry: MetricsRegistry,
) -> None:
    # Starlette prepends each middleware. Register inner layers first so every
    # guard response still receives CORS, security headers, metrics, and request ID.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(settings.trusted_hosts),
    )
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=settings.max_request_body_bytes,
    )
    app.add_middleware(
        RequestTimeoutMiddleware,
        timeout_seconds=settings.request_timeout_seconds,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
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
    app.add_middleware(MetricsMiddleware, registry=metrics_registry)
    app.add_middleware(
        SecurityHeadersMiddleware,
        production=settings.app_env == "production",
        auth_path_prefix=f"{settings.api_v1_prefix}/auth",
    )
    app.add_middleware(RequestContextMiddleware)
    app.state.middleware_names = MIDDLEWARE_REQUEST_ORDER


def register_routers(app: FastAPI, api_v1_prefix: str) -> None:
    router_names: list[str] = []
    router_route_counts: dict[str, int] = {}

    for mount in ROUTER_MOUNTS:
        route_count = len(mount.router.routes)
        if route_count == 0:
            raise RuntimeError(f"Router {mount.name!r} has no routes")

        prefix = api_v1_prefix if mount.versioned else ""
        app.include_router(mount.router, prefix=prefix)
        router_names.append(mount.name)
        router_route_counts[mount.name] = route_count

    app.state.router_names = tuple(router_names)
    app.state.router_route_counts = router_route_counts
    assert_unique_routes(app)
    validate_runtime_contract(app)


def route_manifest(app: FastAPI) -> tuple[RouteManifestEntry, ...]:
    entries: list[RouteManifestEntry] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or methods is None:
            continue

        route_name = str(getattr(route, "name", "unnamed"))
        entries.extend(
            RouteManifestEntry(method=method, path=path, name=route_name)
            for method in methods
        )

    return tuple(sorted(entries))


def assert_unique_routes(app: FastAPI) -> None:
    keys = [(entry.method, entry.path) for entry in route_manifest(app)]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if not duplicates:
        return

    rendered = ", ".join(f"{method} {path}" for method, path in duplicates)
    raise RuntimeError(f"Duplicate API routes detected: {rendered}")
