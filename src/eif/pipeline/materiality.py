"""Materiality engine.

Classifies an event as material or non-material against configurable thresholds.
Non-material events are still stored (they may accumulate or be reinforced later),
but are clearly identifiable so downstream consumers can filter them out.
"""

from __future__ import annotations

from ..config import MaterialityConfig
from ..domain import EconomicEvent
from ..domain.enums import Materiality
from .stages import MaterialityDecision, MaterialityEngine

_REVENUE_METRICS = {"revenue", "gross_margin", "operating_income"}
_COST_METRICS = {
    "cost_of_goods_sold",
    "operating_expenses",
    "capex",
}


class ThresholdMaterialityEngine(MaterialityEngine):
    """Absolute + relative threshold materiality."""

    def __init__(self, config: MaterialityConfig | None = None) -> None:
        self.config = config or MaterialityConfig()

    def assess(self, event: EconomicEvent) -> MaterialityDecision:
        impact = event.primary_impact()
        if impact is None:
            return MaterialityDecision(
                Materiality.UNKNOWN, "no quantified impact to assess materiality against"
            )

        value = abs(impact.estimate.expected_value)
        cfg = self.config

        if value >= cfg.absolute:
            return MaterialityDecision(
                Materiality.MATERIAL,
                f"expected value {value:,.0f} >= absolute threshold {cfg.absolute:,.0f}",
            )

        metric = impact.metric
        if metric in _REVENUE_METRICS and cfg.annual_revenue:
            threshold = cfg.relative_revenue * cfg.annual_revenue
            if value >= threshold:
                return MaterialityDecision(
                    Materiality.MATERIAL,
                    f"expected value {value:,.0f} >= {cfg.relative_revenue:.1%} of revenue",
                )
        if metric in _COST_METRICS and cfg.annual_cost:
            threshold = cfg.relative_cost * cfg.annual_cost
            if value >= threshold:
                return MaterialityDecision(
                    Materiality.MATERIAL,
                    f"expected value {value:,.0f} >= {cfg.relative_cost:.1%} of cost base",
                )

        return MaterialityDecision(
            Materiality.NON_MATERIAL,
            f"expected value {value:,.0f} below configured thresholds",
        )
