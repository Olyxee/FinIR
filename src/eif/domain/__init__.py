"""EIF domain model — typed, first-class economic objects.

Import surface for the whole domain layer. Everything here is a Pydantic model
with strict validation, stable JSON serialization, and mandatory provenance on
derived objects.
"""

from __future__ import annotations

from .base import EIFModel, Money, TimeWindow, utcnow
from .confidence import Confidence, Estimate
from .entity import EconomicEntity, EntityRef
from .enums import (
    Direction,
    EventStatus,
    EvidenceStance,
    ExtractionMethod,
    Materiality,
    Modality,
    RelationshipType,
    SourceType,
)
from .event import EconomicEvent
from .evidence import Evidence, SecurityContext
from .impact import EconomicImpact
from .observation import Claim, Measurement, Observation
from .outcome import RealizedOutcome
from .provenance import (
    Assumption,
    Calculation,
    Citation,
    Decision,
    Provenance,
    deterministic_provenance,
)
from .relationship import EventRelationship

__all__ = [
    # base
    "EIFModel",
    "Money",
    "TimeWindow",
    "utcnow",
    # enums
    "Direction",
    "EventStatus",
    "EvidenceStance",
    "ExtractionMethod",
    "Materiality",
    "Modality",
    "RelationshipType",
    "SourceType",
    # confidence
    "Confidence",
    "Estimate",
    # entities
    "EconomicEntity",
    "EntityRef",
    # evidence
    "Evidence",
    "SecurityContext",
    # observations
    "Observation",
    "Claim",
    "Measurement",
    # events
    "EconomicEvent",
    "EconomicImpact",
    "EventRelationship",
    # outcome
    "RealizedOutcome",
    # provenance
    "Provenance",
    "Citation",
    "Calculation",
    "Assumption",
    "Decision",
    "deterministic_provenance",
]
