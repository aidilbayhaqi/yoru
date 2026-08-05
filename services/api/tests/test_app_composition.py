from __future__ import annotations

from collections import Counter

from fastapi import FastAPI

from yoru_api.app_registry import (
    MIDDLEWARE_CLASS_ORDER,
    MIDDLEWARE_REQUEST_ORDER,
    ROUTER_MOUNTS,
    route_manifest,
)
from yoru_api.runtime_contract import (
    openapi_operations,
    openapi_route_keys,
    registered_router_route_entries,
    registered_router_route_keys,
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

    # The router registry is the declared composition source of truth. OpenAPI is
    # the mounted-runtime proof. Do not depend on app.routes class identity here.
    assert registered_router_route_keys(app) == openapi_route_keys(app, refresh=True)


def test_route_manifest_has_no_duplicate_method_path(app: FastAPI) -> None:
    entries = route_manifest(app)
    keys = [(entry.method, entry.path) for entry in entries]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    assert duplicates == []

    # Every schema route declared by registered routers must also be represented
    # by the app registry manifest used for duplicate detection.
    assert set(registered_router_route_entries(app)) <= set(keys)


def test_middleware_stack_is_complete_and_ordered(app: FastAPI) -> None:
    assert app.state.middleware_names == MIDDLEWARE_REQUEST_ORDER
    assert tuple(item.cls.__name__ for item in app.user_middleware) == MIDDLEWARE_CLASS_ORDER


def test_openapi_contains_every_registered_schema_route(app: FastAPI) -> None:
    assert registered_router_route_keys(app) == openapi_route_keys(app, refresh=True)


def test_openapi_operation_ids_are_unique(app: FastAPI) -> None:
    operations = openapi_operations(app, refresh=True)
    operation_ids = [operation_id for _method, _path, operation_id in operations]

    assert operations
    assert all(operation_id is not None for operation_id in operation_ids)
    assert len(operation_ids) == len(set(operation_ids))
