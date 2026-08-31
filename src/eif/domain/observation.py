"""Observations: structured statements derived from evidence.

An observation is the bridge between raw evidence and economic events. It records
one or more *claims* (natural-language assertions) and any *measurements*
(numeric facts) extracted from evidence, along with the entities involved and the
method/model used. Observations are deliberately event-agnostic: the same
observation may feed several candidate events.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..utils.ids import new_id
from .base import EIFModel
from .confidence import Confidence
from .entity import EntityRef
from .enums import ExtractionMethod
from .provenance import Provenance


class Measurement(EIFModel):
    """A single numeric fact extracted from evidence."""

    name: str = Field(description="What is measured, e.g. 'price_increase_pct', 'annual_spend'.")
    value: float
    unit: str | None = Field(default=None, description="e.g. 'percent', 'ZAR', 'units', 'days'.")
    basis: str | None = Field(
        default=None, description="How the number is grounded, e.g. 'stated', 'derived', 'sum'."
    )


class Claim(EIFModel):
    """A natural-language assertion derived from evidence."""

    text: str
    subject: str | None = None
    predicate: str | None = None


class Observation(EIFModel):
    """A structured statement derived from one or more pieces of evidence."""

    id: str = Field(default_factory=lambda: new_id("observation"))
    evidence_ids: list[str] = Field(default_factory=list)

    observed_at: datetime | None = Field(
        default=None, description="When the observation was made (usually evidence time)."
    )
    effective_at: datetime | None = Field(
        default=None, description="When the observed condition takes/takes effect, if known."
    )

    entities: list[EntityRef] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)

    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    model: str | None = None
    confidence: Confidence = Field(default_factory=lambda: Confidence(score=0.5))
    provenance: Provenance = Field(
        default_factory=lambda: Provenance(producer="ObservationExtractor")
    )

    def measurement(self, name: str) -> Measurement | None:
        """Return the first measurement named ``name`` (or ``None``)."""
        for m in self.measurements:
            if m.name == name:
                return m
        return None

    def summary(self) -> str:
        """One-line human-readable summary of the observation."""
        if self.claims:
            return self.claims[0].text
        if self.measurements:
            m = self.measurements[0]
            return f"{m.name} = {m.value} {m.unit or ''}".strip()
        return f"Observation {self.id}"
