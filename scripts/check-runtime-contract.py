from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from yoru_api.core.settings import Settings  # noqa: E402
from yoru_api.main import create_app  # noqa: E402
from yoru_api.runtime_contract import (  # noqa: E402
    CONTRACT_POLICIES,
    EXPECTED_MIDDLEWARE_CLASS_NAMES,
    EXPECTED_ROUTER_NAMES,
    RUNTIME_CONTRACT_VERSION,
    RUNTIME_STAGE,
    openapi_route_keys,
    validate_runtime_contract,
)


def main() -> int:
    contract_path = ROOT / "openapi" / "runtime-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    expected_document = {
        "schema_version": RUNTIME_CONTRACT_VERSION,
        "stage": RUNTIME_STAGE,
        "routers": list(EXPECTED_ROUTER_NAMES),
        "middleware": list(EXPECTED_MIDDLEWARE_CLASS_NAMES),
        "validation_policies": list(CONTRACT_POLICIES),
    }
    if contract != expected_document:
        print("runtime-contract.json tidak sinkron dengan source contract", file=sys.stderr)
        return 1

    settings = Settings(
        app_env="test",
        database_url="postgresql+asyncpg://yoru:test@localhost:5432/yoru_test",
        cors_allowed_origins="http://localhost:3000,http://localhost:3001",
        trusted_hosts="testserver,localhost",
        session_signing_key="runtime-contract-test-session-key",
        refresh_token_pepper="runtime-contract-test-refresh-pepper",
    )
    app = create_app(settings)
    validate_runtime_contract(app)

    print(
        f"Runtime contract v{RUNTIME_CONTRACT_VERSION} OK · "
        f"{len(EXPECTED_ROUTER_NAMES)} routers · "
        f"{len(openapi_route_keys(app, refresh=True))} OpenAPI operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
