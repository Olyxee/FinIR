# syntax=docker/dockerfile:1
# ---- Economic Intelligence Framework (EIF) API image ----
# Minimal, non-root, offline-capable (deterministic default provider).

FROM python:3.11-slim AS base

# System hygiene + non-root user.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build metadata first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package with the extras needed to serve the API + SQL(+PG) + parsers.
RUN pip install --upgrade pip && \
    pip install ".[api,cli,sql,postgres,excel,pdf]"

# Copy the remaining project assets (benchmarks, research, examples, docs).
COPY benchmarks ./benchmarks
COPY research ./research
COPY examples ./examples
COPY docs ./docs

# Drop privileges.
RUN useradd --create-home --uid 10001 eif && chown -R eif:eif /app
USER eif

ENV EIF_DATABASE_URL=sqlite:////app/data/eif.db \
    EIF_LOG_FORMAT=json
RUN mkdir -p /app/data

EXPOSE 8000

# Container healthcheck hits the liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else sys.exit(1)"

CMD ["uvicorn", "eif.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
