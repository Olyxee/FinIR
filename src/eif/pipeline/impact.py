"""Deterministic impact estimation.

The estimator computes financial consequences using **arithmetic in code**, not
by asking a model "what is the impact?". Each event type maps to a strategy that
looks for the specific structured inputs it needs (a percentage and a spend base,
a stated amount, a duration, ...). If the required inputs are absent, the strategy
returns *no numeric impact* rather than inventing one — the event is still stored,
just without a fabricated number.

Every produced number carries a :class:`Calculation` in its provenance recording
the exact formula and inputs, so any estimate can be audited and reproduced.
"""

from __future__ import annotations

from ..domain import (
    EconomicEvent,
    EconomicImpact,
    Estimate,
    Measurement,
    Observation,
)
from ..domain.enums import Direction
from ..domain.provenance import Calculation, Provenance
from ..ontology.events import EVENT_REGISTRY
from .stages import ImpactEstimator

_PRIMARY_ENTITY_TYPES = {"supplier", "customer", "project", "contract"}


def pool_measurements(event: EconomicEvent, observations: list[Observation]) -> list[Measurement]:
    """Measurements available to an event: its own observations + context ones.

    Mirrors the candidate generator's pooling so the estimator sees the same set
    of signals (e.g. a percentage from an email plus a spend total from a table).
    """
    own_ids = set(event.observation_ids)
    pooled: list[Measurement] = []
    for obs in observations:
        is_context = not any(r.entity_type in _PRIMARY_ENTITY_TYPES for r in obs.entities)
        if obs.id in own_ids or is_context:
            pooled.extend(obs.measurements)
    return pooled


def _first(measurements: list[Measurement], name: str, *, basis_in: tuple[str, ...] | None = None):
    for m in measurements:
        if m.name != name:
            continue
        if basis_in is not None and (m.basis or "").lower() not in basis_in:
            continue
        return m
    return None


def _money_base(measurements: list[Measurement], contexts: tuple[str, ...]) -> Measurement | None:
    """Find a monetary base by context label, falling back to a table column sum."""
    for m in measurements:
        if m.name == "money" and (m.basis or "").lower() in contexts:
            return m
    # Table columns whose header hints at the same concept.
    for m in measurements:
        if m.name == "table_sum" and any(c in (m.basis or "").lower() for c in contexts):
            return m
    # Any table sum as a last resort for spend/revenue.
    for m in measurements:
        if m.name == "table_sum":
            return m
    return None


class DeterministicImpactEstimator(ImpactEstimator):
    """Impact estimator using per-event-type deterministic strategies."""

    def __init__(self, default_currency: str = "ZAR") -> None:
        self.default_currency = default_currency

    def estimate(
        self, event: EconomicEvent, observations: list[Observation]
    ) -> list[EconomicImpact]:
        measurements = pool_measurements(event, observations)
        defn = EVENT_REGISTRY.try_get(event.event_type)
        strategy = defn.impact_strategy if defn else "generic"
        metrics = list(defn.default_metrics) if defn else []
        direction = self._event_direction(event, defn)

        method = getattr(self, f"_strategy_{strategy}", self._strategy_generic)
        impacts = method(event, measurements, metrics, direction)
        for impact in impacts:
            impact.event_id = event.id
        return impacts

    # -- strategies ----------------------------------------------------------
    def _strategy_spend_pct(self, event, measurements, metrics, direction):
        pct = _first(measurements, "percent")
        base = _money_base(measurements, ("spend", "cost", "value"))
        if pct is None or base is None:
            return []
        currency = base.unit if base.unit not in (None, "unknown") else self.default_currency
        exposure = base.value * pct.value / 100.0
        calc = Calculation(
            name="gross_spend_exposure",
            expression="annual_spend * pct / 100",
            inputs={"annual_spend": base.value, "pct": pct.value},
            result=exposure,
            unit=currency,
        )
        metric = metrics[0] if metrics else "cost_of_goods_sold"
        return [
            self._impact(event, metric, direction, exposure, currency, "gross_spend_pct", [calc])
        ]

    def _strategy_revenue_run_rate(self, event, measurements, metrics, direction):
        pct = _first(measurements, "percent")
        base = _money_base(measurements, ("revenue", "sales", "spend", "value"))
        metric = metrics[0] if metrics else "revenue"
        if pct is not None and base is not None:
            currency = base.unit if base.unit not in (None, "unknown") else self.default_currency
            delta = base.value * pct.value / 100.0
            calc = Calculation(
                name="revenue_delta",
                expression="annual_revenue * pct / 100",
                inputs={"annual_revenue": base.value, "pct": pct.value},
                result=delta,
                unit=currency,
            )
            return [
                self._impact(event, metric, direction, delta, currency, "revenue_run_rate", [calc])
            ]
        # Fallback: a stated revenue-at-risk amount.
        amount = _money_base(measurements, ("revenue", "sales", "value"))
        if amount is not None:
            currency = (
                amount.unit if amount.unit not in (None, "unknown") else self.default_currency
            )
            return [
                self._impact(event, metric, direction, amount.value, currency, "stated_amount", [])
            ]
        return []

    def _strategy_fixed_amount(self, event, measurements, metrics, direction):
        amount = _money_base(
            measurements, ("penalty", "obligation", "payable", "amount", "receivable", "value")
        )
        if amount is None:
            return []
        currency = amount.unit if amount.unit not in (None, "unknown") else self.default_currency
        metric = metrics[0] if metrics else "operating_expenses"
        return [self._impact(event, metric, direction, amount.value, currency, "stated_amount", [])]

    def _strategy_delay_cost(self, event, measurements, metrics, direction):
        # Prefer an explicit stated cost/range; otherwise no fabricated number.
        money = [
            m
            for m in measurements
            if m.name == "money" and (m.basis or "") in ("cost", "budget", "amount", "value")
        ]
        metric = metrics[0] if metrics else "operating_expenses"
        if money:
            currency = (
                money[0].unit if money[0].unit not in (None, "unknown") else self.default_currency
            )
            values = sorted(m.value for m in money)
            point = sum(values) / len(values)
            return [
                self._impact_range(
                    event, metric, direction, values[0], point, values[-1], currency, "stated_range"
                )
            ]
        return []

    def _strategy_inventory_delta(self, event, measurements, metrics, direction):
        pct = _first(measurements, "percent")
        base = _money_base(measurements, ("inventory", "value"))
        metric = metrics[0] if metrics else "inventory_value"
        if pct is not None and base is not None:
            currency = base.unit if base.unit not in (None, "unknown") else self.default_currency
            delta = base.value * pct.value / 100.0
            calc = Calculation(
                name="inventory_delta",
                expression="inventory_value * pct / 100",
                inputs={"inventory_value": base.value, "pct": pct.value},
                result=delta,
                unit=currency,
            )
            return [
                self._impact(event, metric, direction, delta, currency, "inventory_delta", [calc])
            ]
        if base is not None:
            currency = base.unit if base.unit not in (None, "unknown") else self.default_currency
            return [
                self._impact(event, metric, direction, base.value, currency, "stated_amount", [])
            ]
        return []

    def _strategy_generic(self, event, measurements, metrics, direction):
        amount = _money_base(measurements, ("amount", "value", "cost"))
        if amount is None:
            return []
        currency = amount.unit if amount.unit not in (None, "unknown") else self.default_currency
        metric = metrics[0] if metrics else "operating_expenses"
        return [self._impact(event, metric, direction, amount.value, currency, "stated_amount", [])]

    # -- builders ------------------------------------------------------------
    def _impact(self, event, metric, direction, point, currency, method, calcs):
        confidence = round(min(0.95, event.confidence.score + 0.05), 3)
        rel_width = 0.2 if calcs else 0.3
        estimate = Estimate.symmetric(
            abs(point),
            rel_width=rel_width,
            unit=currency,
            probability=event.probability,
            confidence=confidence,
        )
        return EconomicImpact(
            metric=metric,
            direction=direction,
            estimate=estimate,
            expected_start=event.effective_at,
            calculation_method=method,
            provenance=Provenance(
                producer="DeterministicImpactEstimator", calculations=list(calcs)
            ),
        )

    def _impact_range(self, event, metric, direction, lower, point, upper, currency, method):
        confidence = round(min(0.9, event.confidence.score), 3)
        estimate = Estimate(
            point=abs(point),
            lower=abs(lower),
            upper=abs(upper),
            unit=currency,
            probability=event.probability,
            confidence=confidence,
        )
        return EconomicImpact(
            metric=metric,
            direction=direction,
            estimate=estimate,
            expected_start=event.effective_at,
            calculation_method=method,
            provenance=Provenance(producer="DeterministicImpactEstimator"),
        )

    def _event_direction(self, event: EconomicEvent, defn) -> Direction:
        if event.magnitude is not None and defn is not None:
            pass
        if defn is not None and defn.typical_direction != Direction.UNKNOWN:
            return Direction(defn.typical_direction)
        return Direction.UNKNOWN
