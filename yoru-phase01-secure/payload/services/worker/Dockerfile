FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system yoru \
    && useradd --system --gid yoru --home-dir /app yoru

COPY services/worker/pyproject.toml ./pyproject.toml
COPY services/worker/src ./src
RUN python -m pip install --no-cache-dir .

USER yoru
CMD ["python", "-m", "yoru_worker.main"]
