FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system yoru \
    && useradd --system --gid yoru --home-dir /app --shell /usr/sbin/nologin yoru \
    && mkdir -p /app/.pytest_cache /tmp/yoru \
    && chown -R yoru:yoru /app /tmp/yoru

COPY services/api/pyproject.toml ./pyproject.toml
COPY services/api/src ./src

# The local image keeps test tooling. Production deployments should use the
# supplied compose override and may split this into runtime/test targets later.
RUN python -m pip install --no-cache-dir ".[dev]" \
    && python -m pip check

COPY --chown=yoru:yoru services/api/tests ./tests
COPY --chown=yoru:yoru services/api/alembic.ini ./alembic.ini
COPY --chown=yoru:yoru services/api/alembic ./alembic

USER yoru

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)" || exit 1

CMD ["uvicorn", "yoru_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header"]
