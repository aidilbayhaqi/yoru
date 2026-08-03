FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system yoru \
    && useradd --system --gid yoru --home-dir /app yoru

COPY services/worker/pyproject.toml ./pyproject.toml
COPY services/worker/src ./src

FROM base AS test
RUN python -m pip install --no-cache-dir ".[dev]" \
    && python -m pip check
COPY services/worker/tests ./tests
USER yoru
CMD ["python", "-m", "pytest", "-q", "-o", "cache_dir=/tmp/pytest-cache"]

FROM base AS runtime
RUN python -m pip install --no-cache-dir . \
    && python -m pip check
USER yoru
CMD ["python", "-m", "yoru_worker.main"]
