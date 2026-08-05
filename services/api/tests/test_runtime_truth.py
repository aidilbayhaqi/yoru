from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from yoru_api.core.middleware import RequestSizeLimitMiddleware
from yoru_api.runtime_contract import (
    EXPECTED_MIDDLEWARE_CLASS_NAMES,
    EXPECTED_ROUTER_NAMES,
    RUNTIME_CONTRACT_VERSION,
    RUNTIME_STAGE,
    openapi_route_keys,
    runtime_schema_route_keys,
    validate_runtime_contract,
)


def test_runtime_contract_accepts_assembled_app(app: FastAPI) -> None:
    validate_runtime_contract(app)
    assert app.state.router_names == EXPECTED_ROUTER_NAMES
    assert tuple(item.cls.__name__ for item in app.user_middleware) == (
        EXPECTED_MIDDLEWARE_CLASS_NAMES
    )


def test_every_registered_router_has_routes(app: FastAPI) -> None:
    counts = app.state.router_route_counts
    assert tuple(counts) == EXPECTED_ROUTER_NAMES
    assert all(isinstance(count, int) and count > 0 for count in counts.values())


def test_metadata_reports_runtime_truth(client: TestClient, app: FastAPI) -> None:
    meta_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.name == "api_metadata"
    )
    response = client.get(meta_route.path)
    assert response.status_code == 200

    payload = response.json()
    assert payload["stage"] == RUNTIME_STAGE
    assert payload["runtime_contract_version"] == RUNTIME_CONTRACT_VERSION
    assert payload["business_modules_enabled"] is True
    assert tuple(payload["modules"]) == EXPECTED_ROUTER_NAMES
    assert payload["features"]["identity"] is True
    assert payload["features"]["mobile_identity"] is True


def test_openapi_matches_runtime_routes(app: FastAPI) -> None:
    assert runtime_schema_route_keys(app) == openapi_route_keys(app)


def test_guard_responses_keep_request_id_security_and_cors(client: TestClient) -> None:
    response = client.get(
        "/health/live",
        headers={
            "Content-Length": str(99_999_999),
            "Origin": "http://localhost:3000",
            "X-Request-ID": "p1-size-limit-test",
        },
    )

    assert response.status_code == 413
    assert response.headers["X-Request-ID"] == "p1-size-limit-test"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.json()["code"] == "REQUEST_BODY_TOO_LARGE"


@pytest.mark.asyncio
async def test_streaming_body_without_content_length_is_limited() -> None:
    consumed = bytearray()

    async def downstream(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            consumed.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestSizeLimitMiddleware(downstream, max_bytes=4)
    incoming: AsyncIterator[Message]

    async def incoming_messages() -> AsyncIterator[Message]:
        yield {"type": "http.request", "body": b"abc", "more_body": True}
        yield {"type": "http.request", "body": b"de", "more_body": False}

    incoming = incoming_messages()

    async def receive() -> Message:
        return await anext(incoming)

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }

    await middleware(scope, receive, send)

    starts = [message for message in sent if message["type"] == "http.response.start"]
    assert starts[-1]["status"] == 413
    assert consumed == b"abc"


def test_unmatched_paths_share_one_metrics_label(client: TestClient, app: FastAPI) -> None:
    assert client.get("/definitely-missing-a").status_code == 404
    assert client.get("/definitely-missing-b").status_code == 404

    snapshot: dict[str, Any] = app.state.metrics_registry.snapshot()
    unmatched = [
        row
        for row in snapshot["requests"]
        if row["method"] == "GET" and row["route"] == "<unmatched>"
    ]
    assert sum(int(row["count"]) for row in unmatched) == 2
