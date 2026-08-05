from __future__ import annotations

from collections import Counter
from typing import Final

from fastapi import FastAPI
from fastapi.routing import APIRoute

RUNTIME_CONTRACT_VERSION: Final[int] = 2
RUNTIME_STAGE: Final[str] = "phase-9-pre-production"
RUNTIME_CONTRACT_MARKER: Final[str] = "YORU_PRIORITY1_RUNTIME_CONTRACT_V4_1"

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

CONTRACT_POLICIES: Final[tuple[str, ...]] = (
    "exact-router-registry",
    "non-empty-router-membership",
    "exact-middleware-order",
    "unique-runtime-route-keys",
    "runtime-openapi-route-parity",
    "unique-openapi-operation-ids",
)


class RuntimeContractError(RuntimeError):
    """Raised when the assembled application no longer matches its release contract."""


def runtime_schema_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    """Return runtime routes that are expected to be represented in OpenAPI."""
    keys: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.include_in_schema:
            continue
        keys.update(
            (method.upper(), route.path)
            for method in route.methods
            if method.upper() not in {"HEAD", "OPTIONS"}
        )
    return keys


def openapi_route_keys(app: FastAPI) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path, path_item in app.openapi().get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                keys.add((method.upper(), path))
    return keys


def _duplicate_runtime_route_keys(app: FastAPI) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or methods is None:
            continue
        keys.extend(
            (method.upper(), path)
            for method in methods
            if method.upper() not in {"HEAD", "OPTIONS"}
        )
    return sorted(key for key, count in Counter(keys).items() if count > 1)


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

    raw_counts = getattr(app.state, "router_route_counts", {})
    router_route_counts = dict(raw_counts) if isinstance(raw_counts, dict) else {}
    if tuple(router_route_counts) != EXPECTED_ROUTER_NAMES:
        errors.append(
            "router count registry mismatch: "
            f"expected={EXPECTED_ROUTER_NAMES!r}, actual={tuple(router_route_counts)!r}"
        )
    empty_routers = sorted(
        name
        for name in EXPECTED_ROUTER_NAMES
        if not isinstance(router_route_counts.get(name), int)
        or router_route_counts.get(name, 0) <= 0
    )
    if empty_routers:
        errors.append(f"registered routers without routes: {empty_routers!r}")

    middleware_names = tuple(item.cls.__name__ for item in app.user_middleware)
    if middleware_names != EXPECTED_MIDDLEWARE_CLASS_NAMES:
        errors.append(
            "middleware order mismatch: "
            f"expected={EXPECTED_MIDDLEWARE_CLASS_NAMES!r}, actual={middleware_names!r}"
        )

    duplicate_runtime_routes = _duplicate_runtime_route_keys(app)
    if duplicate_runtime_routes:
        errors.append(f"duplicate runtime route keys: {duplicate_runtime_routes!r}")

    runtime_routes = runtime_schema_route_keys(app)
    schema_routes = openapi_route_keys(app)
    missing_from_openapi = sorted(runtime_routes - schema_routes)
    unexpected_in_openapi = sorted(schema_routes - runtime_routes)
    if missing_from_openapi:
        errors.append(f"runtime routes missing from OpenAPI: {missing_from_openapi!r}")
    if unexpected_in_openapi:
        errors.append(f"OpenAPI routes missing from runtime: {unexpected_in_openapi!r}")

    duplicate_operation_ids = _duplicate_operation_ids(app)
    if duplicate_operation_ids:
        errors.append(f"duplicate OpenAPI operation IDs: {duplicate_operation_ids!r}")

    if errors:
        raise RuntimeContractError("; ".join(errors))
