"""Provenance and traceability tests."""

from __future__ import annotations

from eif.domain.enums import EvidenceStance
from eif.domain.provenance import (
    Assumption,
    Calculation,
    Citation,
    Provenance,
    deterministic_provenance,
)


def test_supporting_and_contradicting_split():
    prov = Provenance(
        producer="test",
        citations=[
            Citation(evidence_id="ev1", stance=EvidenceStance.SUPPORTS),
            Citation(evidence_id="ev2", stance=EvidenceStance.CONTRADICTS),
            Citation(evidence_id="ev3", stance=EvidenceStance.SUPPORTS),
        ],
    )
    assert prov.supporting_evidence_ids() == ["ev1", "ev3"]
    assert prov.contradicting_evidence_ids() == ["ev2"]


def test_calculation_is_reproducible():
    calc = Calculation(
        name="exposure",
        expression="spend * pct / 100",
        inputs={"spend": 42_000_000, "pct": 10},
        result=4_200_000,
        unit="ZAR",
    )
    # The stored inputs and expression let anyone recompute the number.
    assert calc.inputs["spend"] * calc.inputs["pct"] / 100 == calc.result


def test_provenance_merge_accumulates():
    a = deterministic_provenance("A", citations=[Citation(evidence_id="e1")])
    b = deterministic_provenance(
        "B",
        assumptions=[Assumption(statement="assume flat volume")],
        citations=[Citation(evidence_id="e2")],
    )
    merged = a.merge(b)
    assert len(merged.citations) == 2
    assert len(merged.assumptions) == 1


def test_end_to_end_event_has_full_provenance(eif, supplier_case):
    ev = [e for e in eif.analyze(supplier_case).events if e.event_type == "supplier_price_change"][
        0
    ]
    # every material event must be traceable to its evidence
    assert ev.evidence_ids, "event must reference evidence"
    impact = ev.primary_impact()
    assert impact.provenance.calculations, "impact must record its calculation"
    # provenance notes include the materiality decision
    assert any("materiality" in n for n in ev.provenance.notes)
