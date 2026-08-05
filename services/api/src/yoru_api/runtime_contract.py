from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Final, TypeAlias

from fastapi import FastAPI

RouteKey: TypeAlias = tuple[str, str]

RUNTIME_CONTRACT_VERSION: Final[int] = 4
RUNTIME_STAGE: Final[str] = "phase-9-pre-production"
RUNTIME_CONTRACT_MARKER: Final[str] = "YORU_PRIORITY1_RUNTIME_CONTRACT_V5_1"

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

SCHEMA_HTTP_METHODS: Final[frozenset[str]] = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "TRACE"}
)

CONTRACT_POLICIES: Final[tuple[str, ...]] = (
    "exact-router-registry",
    "router-count-registry-matches-source",
    "non-empty-router-membership",
    "exact-middleware-order",
    "unique-registered-route-keys",
    "registered-router-openapi-parity",
    "unique-openapi-operation-ids",
    "complete-openapi-operation-ids",
    "ci-and-test-contract-validation",
)


class RuntimeContractError(RuntimeError):
    """Raised when the assembled application no longer matches its release contract."""


def _schema_methods(methods: Iterable[object]) -> tuple[str, ...]:
    normalized = {
        str(method).upper()
        for method in methods
        if str(method).upper() in SCHEMA_HTTP_METHODS
    }
    return tuple(sorted(normalized))


def registered_router_route_entries(app: FastAPI) -> tuple[RouteKey, ...]:
    """Build the expected schema route list from the declared router registry.

    This intentionally does not inspect ``app.routes``. The registry is the stable
    composition source of truth, while OpenAPI proves that those routes were mounted.
    """
    from yoru_api.app_registry import ROUTER_MOUNTS

    settings = getattr(app.state, "settings", None)
    api_v1_prefix = getattr(settings, "api_v1_prefix", None)
    if not isinstance(api_v1_prefix, str):
        raise RuntimeContractError("app.state.settings.api_v1_prefix is missing")

    entries: list[RouteKey] = []
    for mount in ROUTER_MOUNTS:
        prefix = api_v1_prefix if mount.versioned else ""
        for route in mount.router.routes:
            if not getattr(route, "include_in_schema", False):
                continue

            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if not isinstance(path, str) or methods is None:
                continue

            full_path = f"{prefix}{path}"
            entries.extend((method, full_path) for method in _schema_methods(methods))

    return tuple(sorted(entries))


def registered_router_route_keys(app: FastAPI) -> set[RouteKey]:
    return set(registered_router_route_entries(app))


def openapi_operations(
    app: FastAPI,
    *,
    refresh: bool = False,
) -> tuple[tuple[str, str, str | None], ...]:
    if refresh:
        app.openapi_schema = None

    operations: list[tuple[str, str, str | None]] = []
    paths = app.openapi().get("paths", {})
    if not isinstance(paths, dict):
        return ()

    for path, path_item in paths.items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        for raw_method, operation in path_item.items():
            method = str(raw_method).upper()
            if method not in SCHEMA_HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            operations.append(
                (
                    method,
                    path,
                    operation_id if isinstance(operation_id, str) else None,
                )
            )

    return tuple(sorted(operations))


def openapi_route_keys(app: FastAPI, *, refresh: bool = False) -> set[RouteKey]:
    return {
        (method, path)
        for method, path, _operation_id in openapi_operations(app, refresh=refresh)
    }


def validate_runtime_contract(app: FastAPI) -> None:
    errors: list[str] = []

    from yoru_api.app_registry import ROUTER_MOUNTS

    declared_names = tuple(mount.name for mount in ROUTER_MOUNTS)
    if declared_names != EXPECTED_ROUTER_NAMES:
        errors.append(
            "declared router registry mismatch: "
            f"expected={EXPECTED_ROUTER_NAMES!r}, actual={declared_names!r}"
        )

    mounted_names = tuple(getattr(app.state, "router_names", ()))
    if mounted_names != EXPECTED_ROUTER_NAMES:
        errors.append(
            "mounted router registry mismatch: "
            f"expected={EXPECTED_ROUTER_NAMES!r}, actual={mounted_names!r}"
        )

    expected_counts = {mount.name: len(mount.router.routes) for mount in ROUTER_MOUNTS}
    raw_counts = getattr(app.state, "router_route_counts", {})
    mounted_counts = dict(raw_counts) if isinstance(raw_counts, dict) else {}
    if mounted_counts != expected_counts:
        errors.append(
            "router count registry mismatch: "
            f"expected={expected_counts!r}, actual={mounted_counts!r}"
        )

    empty_routers = sorted(name for name, count in expected_counts.items() if count <= 0)
    if empty_routers:
        errors.append(f"registered routers without routes: {empty_routers!r}")

    middleware_names = tuple(item.cls.__name__ for item in app.user_middleware)
    if middleware_names != EXPECTED_MIDDLEWARE_CLASS_NAMES:
        errors.append(
            "middleware order mismatch: "
            f"expected={EXPECTED_MIDDLEWARE_CLASS_NAMES!r}, actual={middleware_names!r}"
        )

    registered_entries = registered_router_route_entries(app)
    duplicate_registered_routes = sorted(
        key for key, count in Counter(registered_entries).items() if count > 1
    )
    if duplicate_registered_routes:
        errors.append(
            f"duplicate registered route keys: {duplicate_registered_routes!r}"
        )

    registered_routes = set(registered_entries)
    operations = openapi_operations(app, refresh=True)
    schema_routes = {(method, path) for method, path, _operation_id in operations}

    missing_from_openapi = sorted(registered_routes - schema_routes)
    unexpected_in_openapi = sorted(schema_routes - registered_routes)
    if missing_from_openapi:
        errors.append(f"registered routes missing from OpenAPI: {missing_from_openapi!r}")
    if unexpected_in_openapi:
        errors.append(f"OpenAPI routes absent from router registry: {unexpected_in_openapi!r}")

    missing_operation_ids = sorted(
        (method, path)
        for method, path, operation_id in operations
        if operation_id is None
    )
    if missing_operation_ids:
        errors.append(f"OpenAPI operations without operation IDs: {missing_operation_ids!r}")

    operation_ids = [
        operation_id
        for _method, _path, operation_id in operations
        if operation_id is not None
    ]
    duplicate_operation_ids = sorted(
        operation_id
        for operation_id, count in Counter(operation_ids).items()
        if count > 1
    )
    if duplicate_operation_ids:
        errors.append(f"duplicate OpenAPI operation IDs: {duplicate_operation_ids!r}")

    if errors:
        raise RuntimeContractError("; ".join(errors))
