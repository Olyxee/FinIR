"""Impact estimation + materiality tests."""

from __future__ import annotations

from eif.config import MaterialityConfig
from eif.domain import Confidence, EconomicEvent, EntityRef, Measurement, Observation
from eif.domain.enums import Direction, Materiality
from eif.pipeline.impact import DeterministicImpactEstimator
from eif.pipeline.materiality import ThresholdMaterialityEngine


def _obs(measurements, entity=None):
    ents = [entity] if entity else []
    return Observation(measurements=measurements, entities=ents)


def test_spend_pct_strategy():
    event = EconomicEvent(
        event_type="supplier_price_change",
        confidence=Confidence(score=0.8),
        affected_metrics=["cost_of_goods_sold"],
    )
    obs = _obs(
        [
            Measurement(name="percent", value=10, unit="percent"),
            Measurement(name="money", value=42_000_000, unit="ZAR", basis="spend"),
        ]
    )
    event.observation_ids = [obs.id]
    impacts = DeterministicImpactEstimator().estimate(event, [obs])
    assert len(impacts) == 1
    assert impacts[0].estimate.point == 4_200_000
    assert impacts[0].direction == Direction.INCREASE


def test_no_inputs_no_fabricated_impact():
    event = EconomicEvent(event_type="supplier_price_change", confidence=Confidence(score=0.8))
    obs = _obs([Measurement(name="percent", value=10, unit="percent")])  # no spend base
    event.observation_ids = [obs.id]
    impacts = DeterministicImpactEstimator().estimate(event, [obs])
    assert impacts == []  # honest: no base -> no number


def test_context_measurements_pooled():
    # spend comes from an entity-less (context) observation; pct from the event's obs
    ctx = _obs([Measurement(name="money", value=20_000_000, unit="ZAR", basis="spend")])
    ref = EntityRef(entity_id="en_A", entity_type="supplier", name="ABC")
    own = _obs([Measurement(name="percent", value=5, unit="percent")], entity=ref)
    event = EconomicEvent(
        event_type="supplier_price_change",
        confidence=Confidence(score=0.7),
        observation_ids=[own.id],
    )
    impacts = DeterministicImpactEstimator().estimate(event, [own, ctx])
    assert impacts[0].estimate.point == 1_000_000


def test_fixed_amount_strategy():
    event = EconomicEvent(event_type="contract_obligation", confidence=Confidence(score=0.7))
    obs = _obs([Measurement(name="money", value=2_000_000, unit="ZAR", basis="penalty")])
    event.observation_ids = [obs.id]
    impacts = DeterministicImpactEstimator().estimate(event, [obs])
    assert impacts[0].estimate.point == 2_000_000


def test_materiality_absolute():
    from eif.domain import EconomicImpact, Estimate

    engine = ThresholdMaterialityEngine(MaterialityConfig(absolute=500_000))
    big = EconomicEvent(
        event_type="price_change",
        impacts=[
            EconomicImpact(
                metric="cost_of_goods_sold",
                direction=Direction.INCREASE,
                estimate=Estimate.symmetric(4_200_000, unit="ZAR"),
            )
        ],
    )
    assert engine.assess(big).materiality == Materiality.MATERIAL

    small = EconomicEvent(
        event_type="price_change",
        impacts=[
            EconomicImpact(
                metric="cost_of_goods_sold",
                direction=Direction.INCREASE,
                estimate=Estimate.symmetric(1_000, unit="ZAR"),
            )
        ],
    )
    assert engine.assess(small).materiality == Materiality.NON_MATERIAL


def test_materiality_unknown_without_impact():
    engine = ThresholdMaterialityEngine()
    ev = EconomicEvent(event_type="price_change")
    assert engine.assess(ev).materiality == Materiality.UNKNOWN
