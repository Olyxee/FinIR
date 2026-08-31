"""Deterministic signal extraction tests — the arithmetic-critical layer."""

from __future__ import annotations

from datetime import UTC, datetime

from eif.domain.enums import Direction
from eif.pipeline.signals import (
    extract_entities,
    infer_direction,
    parse_durations_days,
    parse_effective_date,
    parse_labeled_amounts,
    parse_money,
    parse_percentages,
    summarize_pipe_table,
)


def test_parse_money_variants():
    hits = {round(h.value) for h in parse_money("R4.2m and ZAR 42,000,000 and $1.8m and R850k")}
    assert 4_200_000 in hits
    assert 42_000_000 in hits
    assert 1_800_000 in hits
    assert 850_000 in hits


def test_parse_money_does_not_read_scale_from_adjacent_word():
    # "R2,000,000 becomes" must not read the 'b' of becomes as billions.
    (hit,) = parse_money("A penalty of R2,000,000 becomes payable.")
    assert hit.value == 2_000_000


def test_parse_money_ignores_lowercase_r_in_words():
    # 'r' inside "December" must not be treated as the ZAR symbol.
    assert parse_money("due by 31 December 2026") == []


def test_parse_percentages():
    assert parse_percentages("a 10% rise and 2.5% dip") == [10.0, 2.5]


def test_parse_durations_days():
    assert parse_durations_days("delayed by 3 weeks") == [21.0]
    assert parse_durations_days("in 2 months") == [60.0]


def test_infer_direction():
    assert infer_direction("prices will increase") == Direction.INCREASE
    assert infer_direction("orders will decrease") == Direction.DECREASE
    assert infer_direction("no clear signal here") == Direction.NEUTRAL


def test_effective_date_absolute():
    ref = datetime(2026, 8, 30, tzinfo=UTC)
    dt = parse_effective_date("effective 1 November 2026", reference=ref)
    assert dt is not None and dt.year == 2026 and dt.month == 11 and dt.day == 1


def test_effective_date_relative_months():
    ref = datetime(2026, 9, 1, tzinfo=UTC)
    dt = parse_effective_date("this takes effect in two months", reference=ref)
    assert dt is not None and dt.month == 11


def test_effective_date_not_confused_by_on_in_word():
    ref = datetime(2026, 8, 30, tzinfo=UTC)
    dt = parse_effective_date("increase across all precision components", reference=ref)
    assert dt is None


def test_extract_entities_supplier_colon():
    ents = extract_entities("Supplier: ABC Supplies (Pty) Ltd")
    assert any(e.entity_type == "supplier" and e.name == "ABC" for e in ents)


def test_extract_entities_types():
    text = "Customer XYZ and Project Alpha and SKU-A"
    types = {e.entity_type for e in extract_entities(text)}
    assert {"customer", "project", "product"} <= types


def test_labeled_amounts():
    hits = parse_labeled_amounts('{"annual_spend": 42000000}')
    assert hits and hits[0].value == 42_000_000 and hits[0].context == "spend"


def test_summarize_pipe_table():
    text = "product | amount\n--- | ---\nSKU-A | 42000000\nSKU-B | 8000000"
    summary = summarize_pipe_table(text)
    assert summary is not None
    assert summary.row_count == 2
    assert summary.column_sums["amount"] == 50_000_000
