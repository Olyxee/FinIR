"""Economic impact: the estimated financial consequence of an event.

An impact ties an :class:`~eif.domain.confidence.Estimate` to an *affected metric*
(a free string validated against the metric registry) and a direction. It records
the deterministic calculation method used and, once known, the actual realized
value — which is what the feedback loop and evaluation metrics compare against.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..utils.ids import new_id
from .base import EIFModel, TimeWindow
from .confidence import Estimate
from .enums import Direction
from .provenance import Provenance


class EconomicImpact(EIFModel):
    """An estimated (and eventually realized) consequence on a financial metric."""

    id: str = Field(default_factory=lambda: new_id("impact"))
    event_id: str | None = None

    metric: str = Field(description="Affected metric key, e.g. 'cost_of_goods_sold'.")
    direction: Direction = Direction.UNKNOWN
    estimate: Estimate

    horizon: TimeWindow = Field(
        default_factory=TimeWindow, description="Expected start/duration of the impact."
    )
    expected_start: datetime | None = None

    calculation_method: str = Field(
        default="deterministic",
        description="Named method, e.g. 'gross_spend_pct', 'run_rate_delta'.",
    )
    provenance: Provenance = Field(default_factory=lambda: Provenance(producer="ImpactEstimator"))

    # Populated by the feedback loop once the real outcome is observed.
    actual_value: float | None = None
    actual_recorded_at: datetime | None = None

    @property
    def currency(self) -> str | None:
        return self.estimate.unit

    def signed_point(self) -> float:
        """Point estimate with sign applied from direction (decrease => negative)."""
        if self.direction == Direction.DECREASE:
            return -abs(self.estimate.point)
        return self.estimate.point

    def error(self) -> float | None:
        """Signed error (estimate - actual) once the actual value is known."""
        if self.actual_value is None:
            return None
        return self.estimate.point - self.actual_value

    def within_interval(self) -> bool | None:
        """Whether the realized value fell inside [lower, upper] (coverage check)."""
        if self.actual_value is None:
            return None
        return self.estimate.lower <= self.actual_value <= self.estimate.upper
