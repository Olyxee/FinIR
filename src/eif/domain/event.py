"""The Economic Event — the central object of EIF.

An EconomicEvent is a persistent, versioned node in the event graph. It aggregates
the observations and evidence that support it, the entities it involves, its
timing and lifecycle status, a magnitude/probability/confidence, and its estimated
financial impacts. New evidence updates events in place (reinforce / weaken /
contradict / resolve) rather than creating disconnected duplicates.

``event_type`` and ``affected_metrics`` are free strings validated against the
extensible registries in :mod:`eif.ontology`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..utils.ids import new_id
from .base import EIFModel, utcnow
from .confidence import Confidence
from .entity import EntityRef
from .enums import EventStatus, Materiality
from .impact import EconomicImpact
from .provenance import Provenance


class EconomicEvent(EIFModel):
    """A detected economic event with timing, magnitude, uncertainty, and impact."""

    id: str = Field(default_factory=lambda: new_id("event"))
    event_type: str = Field(description="Registered event-type key, e.g. 'supplier_price_change'.")
    title: str | None = None
    organization_id: str | None = None

    status: EventStatus = EventStatus.EMERGING
    materiality: Materiality = Materiality.UNKNOWN

    entities: list[EntityRef] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    # Timing.
    detected_at: datetime = Field(default_factory=utcnow)
    effective_at: datetime | None = None
    expected_resolution_at: datetime | None = None
    resolved_at: datetime | None = None

    # Quantification.
    magnitude: float | None = Field(default=None, description="Primary magnitude (e.g. pct, ZAR).")
    magnitude_unit: str | None = None
    probability: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: Confidence = Field(default_factory=lambda: Confidence(score=0.5))

    affected_metrics: list[str] = Field(default_factory=list)
    impacts: list[EconomicImpact] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    provenance: Provenance = Field(default_factory=lambda: Provenance(producer="EventReasoner"))
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    # ------------------------------------------------------------------ helpers
    def is_material(self) -> bool:
        return self.materiality == Materiality.MATERIAL

    def is_open(self) -> bool:
        return self.status not in (
            EventStatus.RESOLVED,
            EventStatus.DISMISSED,
            EventStatus.SUPERSEDED,
        )

    def entity_ids(self) -> list[str]:
        return [e.entity_id for e in self.entities]

    def primary_impact(self) -> EconomicImpact | None:
        """Return the impact with the largest absolute expected value, if any."""
        if not self.impacts:
            return None
        return max(self.impacts, key=lambda i: abs(i.estimate.expected_value))

    def touch(self) -> None:
        """Bump version and update timestamp after an in-place mutation."""
        self.version += 1
        self.updated_at = utcnow()

    def add_evidence(self, evidence_ids: list[str], observation_ids: list[str]) -> None:
        """Attach new supporting evidence/observations without duplicates."""
        self.evidence_ids = sorted({*self.evidence_ids, *evidence_ids})
        self.observation_ids = sorted({*self.observation_ids, *observation_ids})

    def merge_provenance(self, provenance: Provenance) -> None:
        self.provenance = self.provenance.merge(provenance)
