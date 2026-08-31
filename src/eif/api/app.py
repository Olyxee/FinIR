"""Optional FastAPI service exposing EIF over HTTP.

Versioned under ``/v1`` with automatic OpenAPI docs at ``/docs``. Requires the
``[api]`` extra. There is deliberately no frontend — this is infrastructure.
Endpoints return typed JSON, paginate list results, and surface framework errors
as structured ``{error, message}`` responses.
"""

from __future__ import annotations

from datetime import UTC, datetime

from dateutil import parser as dateparser
from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from ..config import Config
from ..domain import Evidence
from ..domain.outcome import RealizedOutcome as RO
from ..evaluation.eslt import ESLTRecord, compute_eslt
from ..exceptions import EIFError, NotFoundError
from ..facade import EIF
from ..storage.base import EntityQuery, EventQuery
from ..version import __version__
from .schemas import (
    AnalyzeRequest,
    ErrorResponse,
    EvidenceIn,
    HealthResponse,
    OutcomeIn,
    Paginated,
)

_eif: EIF | None = None


def get_eif() -> EIF:
    """Process-wide EIF singleton built from environment/config."""
    global _eif
    if _eif is None:
        _eif = EIF(Config.load())
    return _eif


def create_app(eif: EIF | None = None) -> FastAPI:
    """Application factory (used by tests to inject an in-memory EIF)."""
    global _eif
    if eif is not None:
        _eif = eif

    app = FastAPI(
        title="Economic Intelligence Framework API",
        version=__version__,
        description="Turn multimodal business evidence into economic events with impact & provenance.",
    )

    @app.exception_handler(EIFError)
    async def _eif_error_handler(request: Request, exc: EIFError) -> JSONResponse:
        status = 404 if isinstance(exc, NotFoundError) else 400
        return JSONResponse(
            status_code=status,
            content=ErrorResponse(error=exc.code, message=exc.message).model_dump(),
        )

    @app.get("/health", response_model=HealthResponse, tags=["ops"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @app.get("/ready", response_model=HealthResponse, tags=["ops"])
    def ready(eif: EIF = Depends(get_eif)) -> HealthResponse:
        # Touch the repository to confirm it is reachable.
        eif.repo.stats()
        return HealthResponse(status="ready", version=__version__)

    @app.post("/v1/evidence", tags=["evidence"])
    def post_evidence(body: EvidenceIn, eif: EIF = Depends(get_eif)) -> dict:
        created = _parse_dt(body.created_at)
        evidence = Evidence(
            source=body.source,
            content=body.content,
            modality=body.modality,
            created_at=created,
            metadata=body.metadata,
        )
        eif.repo.add_evidence(evidence)
        return evidence.model_dump(mode="json")

    @app.post("/v1/analyze", tags=["analyze"])
    def analyze(body: AnalyzeRequest, eif: EIF = Depends(get_eif)) -> dict:
        sources: list = [*body.texts, *body.json_items]
        result = eif.analyze(sources)
        return {
            "run_id": result.run_id,
            "evidence": len(result.evidence),
            "observations": len(result.observations),
            "events": [e.model_dump(mode="json") for e in result.events],
        }

    @app.get("/v1/events", tags=["events"])
    def list_events(
        eif: EIF = Depends(get_eif),
        event_type: str | None = None,
        status: str | None = None,
        materiality: str | None = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> Paginated:
        page = eif.repo.list_events(
            EventQuery(
                event_type=event_type,
                status=status,
                materiality=materiality,
                limit=limit,
                offset=offset,
            )
        )
        return _paginate(page)

    @app.get("/v1/events/{event_id}", tags=["events"])
    def get_event(event_id: str, eif: EIF = Depends(get_eif)) -> dict:
        ev = eif.get_event(event_id)
        if ev is None:
            raise NotFoundError(f"event {event_id} not found")
        return ev.model_dump(mode="json")

    @app.get("/v1/entities", tags=["entities"])
    def list_entities(
        eif: EIF = Depends(get_eif),
        entity_type: str | None = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> Paginated:
        page = eif.repo.list_entities(
            EntityQuery(entity_type=entity_type, limit=limit, offset=offset)
        )
        return _paginate(page)

    @app.get("/v1/impacts", tags=["impacts"])
    def list_impacts(
        eif: EIF = Depends(get_eif),
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> Paginated:
        page = eif.repo.list_impacts(limit=limit, offset=offset)
        return _paginate(page)

    @app.post("/v1/outcomes", tags=["outcomes"])
    def post_outcome(body: OutcomeIn, eif: EIF = Depends(get_eif)) -> dict:
        outcome = RO(
            event_id=body.event_id,
            occurred=body.occurred,
            realized_at=_parse_dt(body.realized_at),
            realized_metrics=body.realized_metrics,
            currency=body.currency,
            traditional_detected_at=_parse_dt(body.traditional_detected_at),
            traditional_source=body.traditional_source,
        )
        event = eif.record_outcome(outcome)
        if event is None:
            raise NotFoundError(f"event {body.event_id} not found")
        return event.model_dump(mode="json")

    @app.get("/v1/metrics", tags=["metrics"])
    def metrics(eif: EIF = Depends(get_eif)) -> dict:
        stats = eif.repo.stats()
        records: list[ESLTRecord] = []
        outcomes = eif.repo.list_outcomes(limit=10_000).items
        for outcome in outcomes:
            if outcome.traditional_detected_at is None:
                continue
            event = eif.repo.get_event(outcome.event_id)
            if event is None:
                continue
            records.append(
                ESLTRecord(
                    event_id=event.id,
                    event_type=event.event_type,
                    eif_detected_at=event.detected_at,
                    traditional_detected_at=outcome.traditional_detected_at,
                    traditional_source=outcome.traditional_source,
                )
            )
        return {
            "counts": {
                "evidence": stats.evidence,
                "observations": stats.observations,
                "entities": stats.entities,
                "events": stats.events,
                "outcomes": stats.outcomes,
            },
            "eslt": compute_eslt(records).as_dict(),
        }

    return app


def _paginate(page) -> Paginated:
    return Paginated(
        items=[i.model_dump(mode="json") for i in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        has_more=page.has_more,
    )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = dateparser.parse(value)
    if dt is not None and dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


# Module-level app for `uvicorn eif.api.app:app`.
app = create_app()

__all__ = ["app", "create_app", "get_eif"]
