# YORU_PRIORITY1_RUNTIME_COMPOSITION_V3
from collections import Counter

from fastapi import FastAPI
from fastapi.routing import APIRoute

from yoru_api.app_registry import (
    MIDDLEWARE_CLASS_ORDER,
    MIDDLEWARE_REQUEST_ORDER,
    ROUTER_MOUNTS,
    route_manifest,
)


def test_router_registry_is_nonempty_and_unique() -> None:
    names = [mount.name for mount in ROUTER_MOUNTS]
    assert names
    assert len(names) == len(set(names))
    assert all(mount.router.routes for mount in ROUTER_MOUNTS)


def test_app_mounts_every_registered_router(app: FastAPI) -> None:
    assert app.state.router_names == tuple(mount.name for mount in ROUTER_MOUNTS)
    assert app.state.router_route_counts == {
        mount.name: len(mount.router.routes) for mount in ROUTER_MOUNTS
    }

    actual = {(entry.method, entry.path) for entry in route_manifest(app)}
    expected: set[tuple[str, str]] = set()
    api_v1_prefix = app.state.settings.api_v1_prefix

    for mount in ROUTER_MOUNTS:
        prefix = api_v1_prefix if mount.versioned else ""
        for route in mount.router.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if not isinstance(path, str) or methods is None:
                continue
            expected.update((method, f"{prefix}{path}") for method in methods)

    assert expected <= actual


def test_route_manifest_has_no_duplicate_method_path(app: FastAPI) -> None:
    keys = [(entry.method, entry.path) for entry in route_manifest(app)]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    assert duplicates == []


def test_middleware_stack_is_complete_and_ordered(app: FastAPI) -> None:
    assert app.state.middleware_names == MIDDLEWARE_REQUEST_ORDER
    assert tuple(item.cls.__name__ for item in app.user_middleware) == MIDDLEWARE_CLASS_ORDER


def test_openapi_contains_every_registered_schema_route(app: FastAPI) -> None:
    schema_paths = app.openapi()["paths"]
    api_v1_prefix = app.state.settings.api_v1_prefix

    for mount in ROUTER_MOUNTS:
        prefix = api_v1_prefix if mount.versioned else ""
        for route in mount.router.routes:
            if not isinstance(route, APIRoute) or not route.include_in_schema:
                continue

            path = f"{prefix}{route.path}"
            assert path in schema_paths, f"{mount.name} route missing from OpenAPI: {path}"
            for method in route.methods:
                if method in {"HEAD", "OPTIONS"}:
                    continue
                assert method.lower() in schema_paths[path]


def test_openapi_operation_ids_are_unique(app: FastAPI) -> None:
    operation_ids: list[str] = []
    for path_item in app.openapi()["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str):
                operation_ids.append(operation_id)

    duplicates = sorted(
        operation_id
        for operation_id, count in Counter(operation_ids).items()
        if count > 1
    )
    assert duplicates == []
