.PHONY: install dev infra-up infra-down lint typecheck test build check api worker migrate

install:
	corepack enable
	pnpm install
	python -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e "services/api[dev]" -e "services/worker[dev]"

dev:
	pnpm dev

infra-up:
	docker compose up -d postgres redis qdrant

infra-down:
	docker compose down

lint:
	pnpm lint
	.venv/bin/ruff check services

typecheck:
	pnpm typecheck
	.venv/bin/mypy services/api/src services/worker/src

test:
	pnpm test
	.venv/bin/pytest services/api/tests services/worker/tests

build:
	pnpm build

check: lint typecheck test build

api:
	.venv/bin/uvicorn yoru_api.main:app --app-dir services/api/src --reload --port 8000

worker:
	.venv/bin/python -m yoru_worker.main

migrate:
	.venv/bin/alembic -c services/api/alembic.ini upgrade head
