# YORU_PRIORITY1_RUNTIME_TRUTH_V4
from __future__ import annotations

from collections import Counter
from typing import Final

from fastapi import FastAPI
from fastapi.routing import APIRoute

RUNTIME_CONTRACT_VERSION: Final[int] = 1
RUNTIME_STAGE: Final[str] = "phase-9-pre-production"

EXPECTED_ROUTER_NAMES: Final[tuple[str, ...]] = (
    "health",
    "meta",
    "identity",
    "mobile_identity",
    "partners",
    "catalog",
    "commerce",
    "bookings",
    "finance",
    "advisor",
    "partner_copilot",
    "ops",
)

EXPECTED_MIDDLEWARE_CLASS_NAMES: Final[tuple[str, ...]] = (
    "RequestContextMiddleware",
    "SecurityHeadersMiddleware",
    "MetricsMiddleware",
    "CORSMiddleware",
    "RequestTimeoutMiddleware",
    "RequestSizeLimitMiddleware",
    "TrustedHostMiddleware",
)

# One representative route per mounted module. This catches a module that is
# imported but accidentally empty, versioned incorrectly, or no longer exposed.
REQUIRED_ROUTES: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("GET", "/health/live"),
        ("GET", "/api/v1/meta"),
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/mobile/auth/login"),
        ("POST", "/api/v1/partners"),
        ("GET", "/api/v1/catalog/services/{service_id}"),
        ("POST", "/api/v1/checkout/quote"),
        ("GET", "/api/v1/bookings/{booking_id}"),
        ("GET", "/api/v1/disputes"),
        ("POST", "/api/v1/ai/advisor/sessions"),
        ("GET", "/api/v1/copilot/digest"),
        ("GET", "/api/v1/platform/ops/launch-gates/latest"),
    }
)


class RuntimeContractError(RuntimeError):
    """Raised when the assembled application no longer matches its release contract."""


def _route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or methods is None:
            continue
        keys.update((method, path) for method in methods if method not in {"HEAD", "OPTIONS"})
    return keys


def _schema_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path, path_item in app.openapi().get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                keys.add((method.upper(), path))
    return keys


def _duplicate_operation_ids(app: FastAPI) -> list[str]:
    operation_ids: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.include_in_schema:
            continue
        operation_id = route.operation_id or route.unique_id
        if operation_id:
            operation_ids.append(operation_id)
    return sorted(
        operation_id
        for operation_id, count in Counter(operation_ids).items()
        if count > 1
    )


def validate_runtime_contract(app: FastAPI) -> None:
    errors: list[str] = []

    router_names = tuple(getattr(app.state, "router_names", ()))
    if router_names != EXPECTED_ROUTER_NAMES:
        errors.append(
            "router registry mismatch: "
            f"expected={EXPECTED_ROUTER_NAMES!r}, actual={router_names!r}"
        )

    middleware_names = tuple(item.cls.__name__ for item in app.user_middleware)
    if middleware_names != EXPECTED_MIDDLEWARE_CLASS_NAMES:
        errors.append(
            "middleware order mismatch: "
            f"expected={EXPECTED_MIDDLEWARE_CLASS_NAMES!r}, actual={middleware_names!r}"
        )

    runtime_routes = _route_keys(app)
    missing_runtime = sorted(REQUIRED_ROUTES - runtime_routes)
    if missing_runtime:
        errors.append(f"required runtime routes missing: {missing_runtime!r}")

    schema_routes = _schema_route_keys(app)
    missing_schema = sorted(REQUIRED_ROUTES - schema_routes)
    if missing_schema:
        errors.append(f"required OpenAPI routes missing: {missing_schema!r}")

    duplicate_operation_ids = _duplicate_operation_ids(app)
    if duplicate_operation_ids:
        errors.append(f"duplicate OpenAPI operation IDs: {duplicate_operation_ids!r}")

    if errors:
        raise RuntimeContractError("; ".join(errors))
