"""Detection, impact, and calibration metrics.

These operate on predicted :class:`EconomicEvent` objects versus gold labels
(:class:`GoldEvent`). A predicted event matches a gold event when they share an
event type and at least one entity name (case-insensitive). From the matching we
derive precision / recall / F1, impact MAE / MAPE, interval coverage, and a
confidence-calibration (ECE) estimate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field

from ..domain import EconomicEvent
from ..domain.base import EIFModel


class GoldEvent(EIFModel):
    """A labeled event for benchmarking."""

    event_type: str
    entity_names: list[str] = Field(default_factory=list)
    metric: str | None = None
    impact_value: float | None = None
    currency: str | None = None
    materiality: str | None = None

    def matches(self, event: EconomicEvent) -> bool:
        if event.event_type != self.event_type:
            return False
        if not self.entity_names:
            return True
        gold_names = {n.lower() for n in self.entity_names}
        pred_names = {e.name.lower() for e in event.entities}
        return bool(gold_names & pred_names)


@dataclass
class DetectionMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.fp / (self.fp + self.tp) if (self.fp + self.tp) else 0.0

    def as_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
        }


@dataclass
class ImpactMetrics:
    n: int = 0
    mae: float | None = None
    mape: float | None = None
    interval_coverage: float | None = None

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "mae": _round(self.mae),
            "mape": _round(self.mape),
            "interval_coverage": _round(self.interval_coverage),
        }


@dataclass
class EventMatchPair:
    predicted: EconomicEvent
    gold: GoldEvent


@dataclass
class MatchResult:
    matched: list[EventMatchPair] = field(default_factory=list)
    unmatched_predicted: list[EconomicEvent] = field(default_factory=list)
    unmatched_gold: list[GoldEvent] = field(default_factory=list)

    @property
    def detection(self) -> DetectionMetrics:
        return DetectionMetrics(
            tp=len(self.matched),
            fp=len(self.unmatched_predicted),
            fn=len(self.unmatched_gold),
        )


def match_events(predicted: list[EconomicEvent], gold: list[GoldEvent]) -> MatchResult:
    """Greedily match predicted events to gold events (one-to-one)."""
    result = MatchResult()
    remaining = list(predicted)
    for g in gold:
        hit = next((e for e in remaining if g.matches(e)), None)
        if hit is not None:
            result.matched.append(EventMatchPair(predicted=hit, gold=g))
            remaining.remove(hit)
        else:
            result.unmatched_gold.append(g)
    result.unmatched_predicted = remaining
    return result


def impact_metrics(matched: list[EventMatchPair]) -> ImpactMetrics:
    """MAE / MAPE / interval coverage over matched events with gold impacts."""
    errors: list[float] = []
    abs_pct_errors: list[float] = []
    covered = 0
    counted = 0
    for pair in matched:
        gold = pair.gold
        if gold.impact_value is None:
            continue
        impact = pair.predicted.primary_impact()
        if impact is None:
            continue
        counted += 1
        predicted_value = abs(impact.estimate.point)
        gold_value = abs(gold.impact_value)
        errors.append(abs(predicted_value - gold_value))
        if gold_value != 0:
            abs_pct_errors.append(abs(predicted_value - gold_value) / gold_value)
        if impact.estimate.lower <= gold_value <= impact.estimate.upper:
            covered += 1
    if counted == 0:
        return ImpactMetrics()
    return ImpactMetrics(
        n=counted,
        mae=sum(errors) / len(errors) if errors else None,
        mape=sum(abs_pct_errors) / len(abs_pct_errors) if abs_pct_errors else None,
        interval_coverage=covered / counted,
    )


def calibration_error(confidences: list[float], correct: list[bool], *, bins: int = 5) -> float:
    """Expected Calibration Error (ECE) over equal-width confidence bins."""
    if not confidences or len(confidences) != len(correct):
        return 0.0
    n = len(confidences)
    ece = 0.0
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        idx = [
            i for i, c in enumerate(confidences) if (c > lo or (b == 0 and c == 0.0)) and c <= hi
        ]
        if not idx:
            continue
        avg_conf = sum(confidences[i] for i in idx) / len(idx)
        acc = sum(1 for i in idx if correct[i]) / len(idx)
        ece += (len(idx) / n) * abs(avg_conf - acc)
    return round(ece, 4)


def _round(value: float | None, ndigits: int = 2) -> float | None:
    return None if value is None else round(value, ndigits)
