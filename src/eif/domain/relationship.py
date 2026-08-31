"""Typed relationships between economic events in the event graph."""

from __future__ import annotations

from pydantic import Field

from ..utils.ids import new_id
from .base import EIFModel
from .confidence import Confidence
from .enums import RelationshipType
from .provenance import Provenance


class EventRelationship(EIFModel):
    """A directed, typed edge from one event to another.

    Example: a ``supply_disruption`` event ``causes`` a ``project_delay`` event.
    Relationships carry their own confidence and provenance so the graph remains
    auditable edge by edge.
    """

    id: str = Field(default_factory=lambda: new_id("relationship"))
    source_event_id: str
    target_event_id: str
    type: RelationshipType
    confidence: Confidence = Field(default_factory=lambda: Confidence(score=0.5))
    provenance: Provenance = Field(default_factory=lambda: Provenance(producer="EventReasoner"))
    note: str | None = None
