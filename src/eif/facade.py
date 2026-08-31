"""The high-level ``EIF`` facade — the simplest way to use the framework.

    from eif import EIF

    eif = EIF()
    result = eif.analyze(["supplier_email.txt", "contract.pdf", "spend.csv"])
    for event in result.events:
        print(event.event_type, event.primary_impact())

The facade wires together configuration, storage, the connector registry, and
the pipeline. Everything it does is also available through the lower-level
components for callers who want more control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import Config
from .connectors import ConnectorContext, ConnectorRegistry, default_registry
from .domain import (
    EconomicEntity,
    EconomicEvent,
    Evidence,
    Observation,
    RealizedOutcome,
)
from .graph import EventGraph
from .logging import configure as configure_logging
from .pipeline import EIFPipeline, PipelineResult
from .storage import EntityQuery, EventQuery, Repository, open_repository


@dataclass
class AnalysisResult:
    """Result of an :meth:`EIF.analyze` call."""

    run_id: str
    events: list[EconomicEvent] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    integrations: list[tuple[str, str]] = field(default_factory=list)

    def material_events(self) -> list[EconomicEvent]:
        return [e for e in self.events if e.is_material()]

    @classmethod
    def from_pipeline(cls, result: PipelineResult) -> AnalysisResult:
        return cls(
            run_id=result.run_id,
            events=result.events,
            observations=result.observations,
            evidence=result.evidence,
            integrations=result.integrations,
        )


class EIF:
    """High-level entry point to the Economic Intelligence Framework."""

    def __init__(
        self,
        config: Config | None = None,
        *,
        repo: Repository | None = None,
        database_url: str | None = None,
        registry: ConnectorRegistry | None = None,
        pipeline: EIFPipeline | None = None,
    ) -> None:
        self.config = config or Config.load()
        if database_url is not None:
            self.config.storage.database_url = database_url
        configure_logging(self.config.logging.level, self.config.logging.format)

        self.repo = repo or open_repository(self.config)
        context = ConnectorContext(
            organization_id=self.config.organization.id,
            security=self.config.security,
        )
        self.registry = registry or default_registry(context)
        self.graph = EventGraph(self.repo)
        self.pipeline = pipeline or EIFPipeline(self.repo, config=self.config, graph=self.graph)

    # -- ingestion + analysis -----------------------------------------------
    def load_evidence(self, sources: list[Any]) -> list[Evidence]:
        """Load sources into Evidence without running the pipeline."""
        return self.registry.load_many(sources)

    def analyze(self, sources: list[Any] | Any) -> AnalysisResult:
        """Load ``sources`` and run the full pipeline, returning the result."""
        if not isinstance(sources, list):
            sources = [sources]
        evidence = self.registry.load_many(sources)
        result = self.pipeline.process_evidence(evidence)
        return AnalysisResult.from_pipeline(result)

    def analyze_evidence(self, evidence: list[Evidence]) -> AnalysisResult:
        """Run the pipeline over already-constructed Evidence objects."""
        result = self.pipeline.process_evidence(evidence)
        return AnalysisResult.from_pipeline(result)

    # -- queries -------------------------------------------------------------
    def events(self, query: EventQuery | None = None) -> list[EconomicEvent]:
        return self.repo.list_events(query).items

    def get_event(self, event_id: str) -> EconomicEvent | None:
        return self.repo.get_event(event_id)

    def entities(self, query: EntityQuery | None = None) -> list[EconomicEntity]:
        return self.repo.list_entities(query).items

    def impacts(self, *, limit: int = 50, offset: int = 0):
        return self.repo.list_impacts(limit=limit, offset=offset).items

    # -- feedback loop -------------------------------------------------------
    def record_outcome(self, outcome: RealizedOutcome) -> EconomicEvent | None:
        return self.graph.record_outcome(outcome)

    # -- lifecycle -----------------------------------------------------------
    def close(self) -> None:
        close = getattr(self.repo, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> EIF:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
