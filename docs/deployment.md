# Deployment

EIF is a library; the API and CLI are thin layers on top. Nothing requires a
frontend.

## Local (source)

```bash
pip install -e ".[api,cli,sql]"
eif doctor
uvicorn eif.api.app:app --port 8000
```

## Docker

```bash
docker compose up            # API on SQLite
docker compose --profile pg up   # API on PostgreSQL
```

The image runs as a non-root user, exposes port 8000, and has a `/health`
container healthcheck. Data persists in the `eif-data` volume (SQLite) or the
`eif-pg` volume (Postgres).

## Database: SQLite → PostgreSQL

The same code and schema run on both. Switch by changing one URL:

```bash
# development
EIF_DATABASE_URL=sqlite:///./eif.db

# production
EIF_DATABASE_URL=postgresql+psycopg://eif:eif@db:5432/eif
```

The `SqlRepository` uses a portable document-in-relational layout (indexed columns
+ a JSON payload), so no persistence code changes are needed to move between
backends. `open_repository(config)` creates the schema on first use.

> Migrations: for greenfield deploys the schema is created automatically. For
> managed migrations, install the `[sql]` extra (includes Alembic) and generate
> revisions against `eif.storage.sql.models.Base.metadata`.

## Health & readiness

- `GET /health` — liveness (process up).
- `GET /ready` — readiness (repository reachable).

Both return `{status, version}`.

## Observability

Structured JSON logs carry `run_id`, `event_id`, `organization_id`, `stage`,
`latency_ms`, `provider`, and `model`. Set `EIF_LOG_FORMAT=text` for human-readable
logs in development. OpenTelemetry can be layered in via the optional `[otel]`
extra.

## Scaling notes

- The API is stateless; run multiple replicas behind a load balancer with a shared
  PostgreSQL.
- For continuous ingestion, use the in-process event bus now and swap in a
  Kafka/Redis/NATS adapter later behind the same `EventBus` interface (see
  [../src/eif/bus](../src/eif/bus)).
