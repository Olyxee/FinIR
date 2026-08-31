"""Domain model + schema tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from eif.domain import (
    Confidence,
    EconomicEvent,
    EconomicImpact,
    Estimate,
    Evidence,
    Money,
)
from eif.domain.enums import Direction


def test_evidence_requires_content_or_ref():
    with pytest.raises(PydanticValidationError):
        Evidence(source="x")


def test_evidence_hashes_inline_content():
    ev = Evidence(source="e", content="hello")
    assert ev.content_hash and ev.content_hash.startswith("sha256:")


def test_evidence_effective_time_prefers_created_at(utc_now):
    ev = Evidence(source="e", content="x", created_at=utc_now)
    assert ev.effective_time == utc_now


def test_money_str():
    assert "ZAR" in str(Money(amount=1234.5, currency="ZAR"))


def test_estimate_interval_invariant():
    with pytest.raises(PydanticValidationError):
        Estimate(point=5, lower=6, upper=10)


def test_estimate_symmetric_and_expected_value():
    est = Estimate.symmetric(100.0, rel_width=0.1, probability=0.5)
    assert est.lower == 90 and est.upper == 110
    assert est.expected_value == 50.0


def test_confidence_combine_bounds():
    c = Confidence.combine(model_confidence=1.0, evidence_strength=1.0, conflict_penalty=0.0)
    assert c.score == 1.0
    c2 = Confidence.combine(model_confidence=0.8, evidence_strength=0.5, conflict_penalty=0.5)
    assert 0.0 <= c2.score <= 1.0


def test_event_roundtrip_json():
    impact = EconomicImpact(
        metric="cost_of_goods_sold",
        direction=Direction.INCREASE,
        estimate=Estimate.symmetric(4_200_000, unit="ZAR"),
    )
    event = EconomicEvent(event_type="supplier_price_change", impacts=[impact])
    dumped = event.model_dump(mode="json")
    restored = EconomicEvent.model_validate(dumped)
    assert restored.event_type == "supplier_price_change"
    assert restored.primary_impact().estimate.point == 4_200_000


def test_event_touch_bumps_version():
    event = EconomicEvent(event_type="price_change")
    v = event.version
    event.touch()
    assert event.version == v + 1


def test_event_extra_fields_forbidden():
    with pytest.raises(PydanticValidationError):
        EconomicEvent(event_type="price_change", bogus_field=1)


def test_impact_error_and_coverage():
    est = Estimate(point=100, lower=80, upper=120, unit="ZAR")
    imp = EconomicImpact(metric="revenue", direction=Direction.DECREASE, estimate=est)
    assert imp.error() is None
    imp.actual_value = 90
    assert imp.error() == 10
    assert imp.within_interval() is True
    imp.actual_value = 200
    assert imp.within_interval() is False
