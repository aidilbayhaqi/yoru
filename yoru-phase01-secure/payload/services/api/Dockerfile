FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system yoru \
    && useradd --system --gid yoru --home-dir /app yoru

COPY services/api/pyproject.toml ./pyproject.toml
COPY services/api/src ./src
RUN python -m pip install --no-cache-dir .

COPY services/api/alembic.ini ./alembic.ini
COPY services/api/alembic ./alembic

USER yoru
EXPOSE 8000
CMD ["uvicorn", "yoru_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
