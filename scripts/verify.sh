#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build

"$project_root/.venv/bin/ruff" check services
"$project_root/.venv/bin/mypy" services/api/src services/worker/src
"$project_root/.venv/bin/pytest" services/api/tests services/worker/tests
"$project_root/.venv/bin/alembic" -c services/api/alembic.ini upgrade head --sql >/dev/null
