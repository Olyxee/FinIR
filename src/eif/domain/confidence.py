"""Confidence and uncertainty primitives.

EIF keeps uncertainty explicit and refuses to present uncertain estimates as
facts. Two complementary objects capture this:

* :class:`Confidence` — a 0..1 belief that a claim/event is real, decomposed into
  contributing factors (model confidence, evidence strength, conflict penalty).
* :class:`Estimate` — a numeric point estimate with a [lower, upper] interval,
  a probability of occurrence, and a confidence in the estimate itself.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import EIFModel


class Confidence(EIFModel):
    """A calibrated belief that something is true, in [0, 1].

    ``score`` is the headline number. The factors are recorded for transparency
    and let downstream code re-weight without re-running the model.
    """

    score: float = Field(ge=0.0, le=1.0)
    model_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    conflict_penalty: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Reduction applied due to contradicting evidence."
    )
    rationale: str | None = None

    @classmethod
    def combine(
        cls,
        *,
        model_confidence: float,
        evidence_strength: float,
        conflict_penalty: float = 0.0,
        rationale: str | None = None,
    ) -> Confidence:
        """Deterministically combine factors into a single score.

        score = model_confidence * evidence_strength * (1 - conflict_penalty),
        clamped to [0, 1]. This is intentionally simple and inspectable rather
        than a hidden learned function.
        """
        raw = model_confidence * evidence_strength * (1.0 - conflict_penalty)
        score = max(0.0, min(1.0, raw))
        return cls(
            score=score,
            model_confidence=model_confidence,
            evidence_strength=evidence_strength,
            conflict_penalty=conflict_penalty,
            rationale=rationale,
        )


class Estimate(EIFModel):
    """A numeric estimate with an uncertainty interval and probability.

    Invariants (enforced): ``lower <= point <= upper``. ``probability`` is the
    chance the underlying event occurs at all; ``confidence`` is how much to
    trust the estimate given the event occurs.
    """

    point: float
    lower: float
    upper: float
    unit: str | None = Field(default=None, description="Currency code or metric unit.")
    probability: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_interval(self) -> Estimate:
        if not (self.lower <= self.point <= self.upper):
            raise ValueError(
                f"estimate interval invalid: lower={self.lower} point={self.point} "
                f"upper={self.upper} (require lower <= point <= upper)"
            )
        return self

    @property
    def expected_value(self) -> float:
        """Probability-weighted point estimate (point * probability)."""
        return self.point * self.probability

    def interval_width(self) -> float:
        return self.upper - self.lower

    @classmethod
    def symmetric(
        cls,
        point: float,
        *,
        rel_width: float = 0.2,
        unit: str | None = None,
        probability: float = 1.0,
        confidence: float = 0.5,
    ) -> Estimate:
        """Build an estimate with a symmetric +/- ``rel_width`` interval."""
        delta = abs(point) * rel_width
        return cls(
            point=point,
            lower=point - delta,
            upper=point + delta,
            unit=unit,
            probability=probability,
            confidence=confidence,
        )
