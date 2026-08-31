"""ESLT and metrics tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eif.domain import Confidence, EconomicEvent, EconomicImpact, EntityRef, Estimate
from eif.domain.enums import Direction
from eif.evaluation import (
    GoldEvent,
    calibration_error,
    compute_eslt,
    impact_metrics,
    match_events,
)
from eif.evaluation.eslt import ESLTRecord


def test_eslt_positive_lead_time():
    base = datetime(2026, 9, 3, tzinfo=UTC)
    records = [
        ESLTRecord(
            event_id="e1",
            event_type="supplier_price_change",
            eif_detected_at=base,
            traditional_detected_at=base + timedelta(days=48),
        )
    ]
    summary = compute_eslt(records)
    assert summary.n == 1
    assert summary.mean_days == 48.0
    assert summary.positive_fraction == 1.0


def test_eslt_empty():
    assert compute_eslt([]).n == 0


def _event(entity="ABC", point=4_200_000):
    ref = EntityRef(entity_id="en", entity_type="supplier", name=entity)
    return EconomicEvent(
        event_type="supplier_price_change",
        entities=[ref],
        confidence=Confidence(score=0.9),
        impacts=[
            EconomicImpact(
                metric="cost_of_goods_sold",
                direction=Direction.INCREASE,
                estimate=Estimate.symmetric(point, unit="ZAR"),
            )
        ],
    )


def test_match_and_detection_metrics():
    gold = [GoldEvent(event_type="supplier_price_change", entity_names=["ABC"])]
    result = match_events([_event("ABC")], gold)
    d = result.detection
    assert d.tp == 1 and d.fp == 0 and d.fn == 0 and d.precision == 1.0

    # false positive + false negative
    result2 = match_events([_event("DEF")], gold)
    assert result2.detection.fp == 1 and result2.detection.fn == 1


def test_impact_metrics_mae_and_coverage():
    gold = [
        GoldEvent(
            event_type="supplier_price_change",
            entity_names=["ABC"],
            metric="cost_of_goods_sold",
            impact_value=4_000_000,
        )
    ]
    result = match_events([_event("ABC", point=4_200_000)], gold)
    m = impact_metrics(result.matched)
    assert m.n == 1
    assert m.mae == 200_000
    assert m.interval_coverage == 1.0  # 4.0m within +/-20% of 4.2m


def test_calibration_error():
    # perfectly calibrated: high-confidence correct, low-confidence wrong
    ece = calibration_error([0.9, 0.9, 0.1, 0.1], [True, True, False, False])
    assert ece < 0.2
