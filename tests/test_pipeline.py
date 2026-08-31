"""End-to-end pipeline and facade tests."""

from __future__ import annotations

from eif import EIF
from eif.domain.enums import Direction, Materiality


def test_supplier_scenario_end_to_end(eif, supplier_case):
    result = eif.analyze(supplier_case)
    assert len(result.evidence) == 2
    events = result.events
    supplier_events = [e for e in events if e.event_type == "supplier_price_change"]
    assert len(supplier_events) == 1

    ev = supplier_events[0]
    assert ev.materiality == Materiality.MATERIAL
    assert ev.effective_at is not None and ev.effective_at.month == 11

    impact = ev.primary_impact()
    assert impact.metric == "cost_of_goods_sold"
    assert impact.direction == Direction.INCREASE
    assert impact.estimate.point == 4_200_000
    # provenance records the deterministic calculation
    calcs = impact.provenance.calculations
    assert calcs and calcs[0].result == 4_200_000


def test_no_duplicate_generic_price_change(eif, supplier_case):
    result = eif.analyze(supplier_case)
    types = [e.event_type for e in result.events]
    assert "price_change" not in types  # suppressed when a supplier is named


def test_entities_resolved_and_persisted(eif, supplier_case):
    eif.analyze(supplier_case)
    entities = eif.entities()
    names = {e.name for e in entities}
    assert "ABC" in names
    assert "SKU-A" in names


def test_reanalyze_reinforces_same_event(eif, supplier_case):
    r1 = eif.analyze(supplier_case)
    r2 = eif.analyze(supplier_case)
    id1 = [e for e in r1.events if e.event_type == "supplier_price_change"][0].id
    id2 = [e for e in r2.events if e.event_type == "supplier_price_change"][0].id
    assert id1 == id2  # integrated, not duplicated
    assert eif.repo.stats().events == 1


def test_pipeline_is_deterministic(config, supplier_case):
    e1 = EIF(config)
    e2 = EIF(config)
    p1 = e1.analyze(supplier_case).events[0].primary_impact().estimate.point
    p2 = e2.analyze(supplier_case).events[0].primary_impact().estimate.point
    assert p1 == p2


def test_analyze_single_source(eif):
    result = eif.analyze("Supplier ABC will raise prices 8% on SKU-A. Annual spend R10,000,000.")
    assert any(e.event_type == "supplier_price_change" for e in result.events)
