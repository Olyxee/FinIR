"""Provenance: the audit trail behind every derived conclusion.

Provenance is mandatory in EIF. Every observation, event, and impact carries a
:class:`Provenance` record answering: which evidence, which model/version, which
deterministic calculations, which assumptions, and which supporting/contradicting
citations produced this conclusion.

Note: EIF deliberately does **not** store raw model chain-of-thought. It stores
*structured* reasoning artifacts — citations, calculations, assumptions, and
decisions — which are auditable without exposing opaque private reasoning.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..version import __version__
from .base import EIFModel, utcnow
from .enums import EvidenceStance, ExtractionMethod


class Citation(EIFModel):
    """A pointer from a conclusion back into a specific piece of evidence."""

    evidence_id: str
    locator: str | None = Field(
        default=None,
        description="Where in the evidence, e.g. 'line 12', 'page 3', 'cell B7', 'char 40-88'.",
    )
    snippet: str | None = Field(
        default=None, description="Short (possibly redacted) supporting excerpt."
    )
    stance: EvidenceStance = EvidenceStance.SUPPORTS


class Calculation(EIFModel):
    """A deterministic computation performed in code (never by the model).

    Storing the human-readable expression and the concrete inputs/result makes
    every number reproducible and auditable.
    """

    name: str
    expression: str = Field(description="Human-readable formula, e.g. 'spend * pct_increase'.")
    inputs: dict[str, float] = Field(default_factory=dict)
    result: float
    unit: str | None = None


class Assumption(EIFModel):
    """An interpretive assumption introduced during reasoning."""

    statement: str
    method: ExtractionMethod = ExtractionMethod.LLM
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str | None = Field(default=None, description="Model name or 'default'/'human'.")


class Decision(EIFModel):
    """A recorded decision taken by a pipeline stage (e.g. entity match, merge)."""

    stage: str
    description: str
    method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    details: dict[str, str] = Field(default_factory=dict)


class Provenance(EIFModel):
    """The complete, structured audit trail for a derived object."""

    created_at: datetime = Field(default_factory=utcnow)
    producer: str = Field(description="Component that produced the object, e.g. 'ImpactEstimator'.")
    method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    model: str | None = None
    model_version: str | None = None
    framework_version: str = __version__
    pipeline_run_id: str | None = None

    citations: list[Citation] = Field(default_factory=list)
    calculations: list[Calculation] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def supporting_evidence_ids(self) -> list[str]:
        """Distinct evidence ids cited as supporting this conclusion."""
        return sorted(
            {c.evidence_id for c in self.citations if c.stance == EvidenceStance.SUPPORTS}
        )

    def contradicting_evidence_ids(self) -> list[str]:
        """Distinct evidence ids cited as contradicting this conclusion."""
        return sorted(
            {c.evidence_id for c in self.citations if c.stance == EvidenceStance.CONTRADICTS}
        )

    def merge(self, other: Provenance) -> Provenance:
        """Return a new provenance combining this record with ``other``.

        Used when evidence reinforces an existing event: citations, calculations,
        assumptions, and decisions accumulate rather than overwrite.
        """
        return Provenance(
            created_at=self.created_at,
            producer=self.producer,
            method=self.method,
            model=self.model or other.model,
            model_version=self.model_version or other.model_version,
            pipeline_run_id=self.pipeline_run_id or other.pipeline_run_id,
            citations=[*self.citations, *other.citations],
            calculations=[*self.calculations, *other.calculations],
            assumptions=[*self.assumptions, *other.assumptions],
            decisions=[*self.decisions, *other.decisions],
            notes=[*self.notes, *other.notes],
        )


def deterministic_provenance(producer: str, **kwargs: object) -> Provenance:
    """Convenience constructor for a deterministic provenance record."""
    return Provenance(producer=producer, method=ExtractionMethod.DETERMINISTIC, **kwargs)
