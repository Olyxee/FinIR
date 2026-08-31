"""Economic Signal Lead Time (ESLT).

ESLT measures how much *earlier* EIF identifies an economically meaningful event
than a conventional, structured financial indicator would::

    ESLT = traditional_detected_at - eif_detected_at   (in days)

A positive ESLT means EIF flagged the event earlier. ESLT is only defined for
events that both EIF detected and for which a traditional-detection timestamp is
known (recorded on the realized outcome). We report per-event values plus a
distribution summary; we make no efficacy claim beyond what the data shows.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ESLTRecord:
    event_id: str
    event_type: str
    eif_detected_at: datetime
    traditional_detected_at: datetime
    traditional_source: str | None = None

    @property
    def lead_time_days(self) -> float:
        return (self.traditional_detected_at - self.eif_detected_at).total_seconds() / 86400.0


@dataclass
class ESLTSummary:
    n: int = 0
    mean_days: float | None = None
    median_days: float | None = None
    stdev_days: float | None = None
    min_days: float | None = None
    max_days: float | None = None
    ci95_low: float | None = None
    ci95_high: float | None = None
    positive_fraction: float | None = None
    records: list[ESLTRecord] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "mean_days": _round(self.mean_days),
            "median_days": _round(self.median_days),
            "stdev_days": _round(self.stdev_days),
            "min_days": _round(self.min_days),
            "max_days": _round(self.max_days),
            "ci95_low": _round(self.ci95_low),
            "ci95_high": _round(self.ci95_high),
            "positive_fraction": _round(self.positive_fraction),
        }


def compute_eslt(records: list[ESLTRecord]) -> ESLTSummary:
    """Summarize a set of ESLT records with a normal-approximation 95% CI."""
    if not records:
        return ESLTSummary()
    values = [r.lead_time_days for r in records]
    n = len(values)
    mean = statistics.fmean(values)
    median = statistics.median(values)
    stdev = statistics.stdev(values) if n > 1 else 0.0
    positive = sum(1 for v in values if v > 0) / n

    ci_low = ci_high = mean
    if n > 1 and stdev > 0:
        margin = 1.96 * stdev / math.sqrt(n)
        ci_low, ci_high = mean - margin, mean + margin

    return ESLTSummary(
        n=n,
        mean_days=mean,
        median_days=median,
        stdev_days=stdev,
        min_days=min(values),
        max_days=max(values),
        ci95_low=ci_low,
        ci95_high=ci_high,
        positive_fraction=positive,
        records=records,
    )


def _round(value: float | None, ndigits: int = 2) -> float | None:
    return None if value is None else round(value, ndigits)
