"""Incremental runtime tests — the central correctness + reuse properties."""

from __future__ import annotations

import numpy as np

from finir import FinancialModel
from finir.runtime.state import ModelState


def _model() -> FinancialModel:
    m = FinancialModel()
    for n, v in [
        ("revenue", 500e6),
        ("cogs", 300e6),
        ("opex", 120e6),
        ("debt", 80e6),
        ("rate", 0.11),
    ]:
        m.input(n, v, currency=None if n == "rate" else "ZAR")
    m.define("gross_profit", "revenue - cogs")
    m.define("ebitda", "gross_profit - opex", output=True)
    m.define("interest", "debt * rate", output=True)  # independent of cogs
    m.define("opex_ratio", "opex / revenue", output=True)  # independent of cogs
    return m


def test_base_evaluation_values():
    m = _model()
    r = m.evaluate()
    assert r["ebitda"] == 80e6
    assert abs(r["opex_ratio"] - 0.24) < 1e-9


def test_only_affected_nodes_recompute():
    m = _model()
    m.evaluate()
    r = m.what_if(cogs="+4%")
    # cogs change dirties exactly gross_profit + ebitda.
    assert set(r.recomputed) == {"gross_profit", "ebitda"}
    # cogs-independent outputs are reused, not recomputed.
    assert set(r.reused) == {"interest", "opex_ratio"}


def test_repeat_evaluation_full_reuse():
    m = _model()
    m.evaluate()
    r = m.evaluate()  # nothing changed
    assert r.recomputed == []
    assert set(r.reused) >= {"gross_profit", "ebitda", "interest", "opex_ratio"}


def test_set_input_invalidates_downstream_only():
    m = _model()
    m.evaluate()
    assert m.dirty_nodes("cogs") == ["cogs", "ebitda", "gross_profit"]
    assert m.dirty_nodes("debt") == ["debt", "interest"]


def test_scenarios_reuse_base():
    m = _model()
    m.evaluate()
    sc = m.scenarios({"base": {}, "up": {"revenue": "+10%"}})
    assert round(float(sc["up"]["ebitda"])) == 130_000_000
    # In the revenue scenario, cogs-only-independent 'interest' is reused.
    assert "interest" in sc["up"].reused


def test_scenario_batch_vectorized():
    m = _model()
    m.evaluate()
    r = m.run_scenarios(cogs=np.linspace(300e6, 400e6, 1000))
    assert r["ebitda"].shape == (1000,)
    assert round(float(r["ebitda"][0])) == 80_000_000


def test_state_snapshots_chain():
    m = _model()
    m.evaluate()
    base = m.state()
    s1 = base.with_change("cogs", relative=0.04)
    s2 = s1.with_change("revenue", relative=-0.10)
    assert s1.changed == ("cogs",)
    assert isinstance(s2, ModelState)
    r = m.evaluate_state(s2)
    # revenue -10% and cogs +4%
    assert round(float(r["ebitda"])) == round(500e6 * 0.9 - 300e6 * 1.04 - 120e6)


def test_change_specs():
    from finir.runtime.scenario import resolve_change

    assert resolve_change(100.0, "+8%") == 108.0
    assert resolve_change(100.0, "-8%") == 92.0
    assert resolve_change(30.0, "30d->60d") == 60.0
    assert resolve_change(30.0, 60) == 60.0
    assert resolve_change(100.0, {"relative": 0.5}) == 150.0
