# Yoru release discipline

`.yoru-release.json` is the release source of truth for the application release version, phase, and Alembic head.

The following artifacts must carry the same application version:

- root `package.json`
- storefront `package.json`
- console `package.json`
- API `pyproject.toml`
- API `__version__`
- worker `pyproject.toml`
- Docker Compose `APP_VERSION` default

Workspace libraries such as `@yoru/contracts` and `@yoru/ui` may use independent package versions.

Run before every merge and release:

```bash
python scripts/check-release-consistency.py
pnpm check
docker compose build api worker storefront console
docker compose run --rm migrate
docker compose run --rm api python -m pytest -q -o cache_dir=/tmp/pytest-cache
docker compose run --rm worker python -m pytest -q -o cache_dir=/tmp/pytest-cache
```

Record the Git commit SHA as the container image label or deployment release ID. Never use backup folders inside the tracked repository as release history; use commits, tags, and release artifacts.
