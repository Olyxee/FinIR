"""Model API, backends/dispatch, intent, safe-numerics, persistence, extension."""

from __future__ import annotations

import numpy as np
import pytest

import finir
from finir import FinancialModel, MockIntentCompiler, kernel
from finir.backends.dispatch import BackendPlanner, WorkloadProfile
from finir.exceptions import NumericError
from finir.numerics import NumericPolicy, safe_div, set_policy
from finir.types import Money


def test_model_save_load_roundtrip(tmp_path):
    m = FinancialModel()
    m.input("revenue", 500e6, currency="ZAR")
    m.input("cogs", 300e6, currency="ZAR")
    m.define("gp", "revenue - cogs", output=True)
    m.evaluate()
    path = tmp_path / "model.finir.json"
    m.save(path)
    m2 = FinancialModel.load(path)
    assert m2.evaluate()["gp"] == 200e6


def test_apply_intent_variants():
    m = FinancialModel()
    m.input("cogs", 300e6, currency="ZAR")
    m.input("revenue", 500e6, currency="ZAR")
    m.define("gp", "revenue - cogs", output=True)
    m.evaluate()
    r = m.apply_intent({"operation": "relative_change", "target": "cogs", "value": 0.04})
    assert round(float(r["gp"])) == round(500e6 - 300e6 * 1.04)
    r2 = m.apply_intent({"operation": "set", "target": "revenue", "value": 600e6})
    assert round(float(r2["gp"])) == round(600e6 - 300e6)


def test_mock_intent_compiler():
    ic = MockIntentCompiler()
    assert ic.compile("increase COGS by 4%") == {
        "operation": "relative_change",
        "target": "cogs",
        "value": 0.04,
    }
    out = ic.compile("extend payment terms from 30 to 60 days")
    assert out == {"operation": "set", "target": "payment_terms", "value": 60.0}


def test_backend_planner_thresholds():
    planner = BackendPlanner(gpu_min_elements=1000)
    small = planner.choose(WorkloadProfile(scenario_size=1))
    assert small.backend.name == "cpu"
    big = planner.choose(WorkloadProfile(scenario_size=5000))
    # No GPU in CI -> falls back to CPU but records the reason.
    assert big.backend.name == "cpu"


def test_gpu_unavailable_is_graceful():
    from finir.backends.gpu import gpu_available

    assert gpu_available() in (True, False)  # never raises


def test_safe_div_policies():
    assert np.isnan(safe_div(1.0, 0.0))
    set_policy(NumericPolicy(on_div_zero="zero"))
    assert safe_div(1.0, 0.0) == 0.0
    set_policy(NumericPolicy(on_div_zero="raise"))
    with pytest.raises(NumericError):
        safe_div(1.0, 0.0)
    set_policy(NumericPolicy())  # reset to default


def test_custom_kernel_extension():
    @kernel("logistics.landed_cost", result=Money("ZAR"), arity=2)
    def landed(unit_cost, freight):
        return unit_cost + freight

    m = FinancialModel()
    m.input("unit_cost", 100.0, currency="ZAR")
    m.input("freight", 20.0, currency="ZAR")
    m.define("landed_cost", "logistics.landed_cost(unit_cost, freight)", output=True)
    assert m.evaluate()["landed_cost"] == 120.0


def test_public_parse_and_compile():
    module = finir.parse("model m { input a: scalar\n b = a * 2\n output b }")
    compiled = finir.compile_model(module)
    assert "type_check" in compiled.report.passes
