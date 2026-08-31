"""Event graph + resolution tests."""

from __future__ import annotations

from eif.domain import (
    Confidence,
    EconomicEvent,
    EconomicImpact,
    EntityRef,
    Estimate,
    RealizedOutcome,
)
from eif.domain.enums import Direction, EventStatus, RelationshipType
from eif.graph import ACTION_NEW, ACTION_REINFORCE, EventGraph
from eif.storage import open_repository


def _event(direction=Direction.INCREASE, score=0.7, entity_id="en_ABC"):
    ref = EntityRef(entity_id=entity_id, entity_type="supplier", name="ABC")
    impact = EconomicImpact(
        metric="cost_of_goods_sold",
        direction=direction,
        estimate=Estimate.symmetric(4_000_000, unit="ZAR", confidence=0.8),
    )
    return EconomicEvent(
        event_type="supplier_price_change",
        organization_id="o",
        entities=[ref],
        impacts=[impact],
        confidence=Confidence(score=score),
    )


def test_new_event_created():
    g = EventGraph(open_repository("memory"))
    r = g.integrate(_event())
    assert r.action == ACTION_NEW and r.created


def test_reinforce_raises_confidence_and_confirms():
    g = EventGraph(open_repository("memory"))
    r1 = g.integrate(_event(score=0.6))
    r2 = g.integrate(_event(score=0.6))
    assert r2.action == ACTION_REINFORCE
    assert r1.event.id == r2.event.id
    assert r2.event.confidence.score > 0.6
    assert r2.event.status == EventStatus.CONFIRMED
    assert r2.event.version == 2


def test_contradiction_weakens():
    g = EventGraph(open_repository("memory"))
    g.integrate(_event(direction=Direction.INCREASE, score=0.8))
    r = g.integrate(_event(direction=Direction.DECREASE, score=0.8))
    assert r.event.status == EventStatus.WEAKENED
    assert r.event.confidence.score < 0.8


def test_distinct_entities_not_merged():
    g = EventGraph(open_repository("memory"))
    g.integrate(_event(entity_id="en_ABC"))
    r = g.integrate(_event(entity_id="en_DEF"))
    assert r.action == ACTION_NEW


def test_relationships_and_neighbors():
    repo = open_repository("memory")
    g = EventGraph(repo)
    a = g.integrate(_event(entity_id="en_A")).event
    b = g.integrate(_event(entity_id="en_B")).event
    g.relate(a.id, b.id, RelationshipType.CAUSES)
    neighbors = g.neighbors(a.id)
    assert b.id in {n.id for n in neighbors}


def test_record_outcome_resolves_event():
    repo = open_repository("memory")
    g = EventGraph(repo)
    ev = g.integrate(_event()).event
    updated = g.record_outcome(
        RealizedOutcome(event_id=ev.id, realized_metrics={"cost_of_goods_sold": 3_900_000})
    )
    assert updated.status == EventStatus.RESOLVED
    assert updated.impacts[0].actual_value == 3_900_000
