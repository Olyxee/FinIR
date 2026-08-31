"""Kernel value tests — compared against trusted closed-form results."""

from __future__ import annotations

import math

import numpy as np

from finir.kernels.registry import default_registry


def k(name, *args):
    return default_registry().call(name, list(args))


def test_corporate_kernels():
    assert k("gross_profit", 500.0, 300.0) == 200.0
    assert math.isclose(k("gross_margin", 200.0, 500.0), 0.4)
    assert k("ebitda", 200.0, 120.0) == 80.0
    assert math.isclose(k("ebitda_margin", 80.0, 500.0), 0.16)


def test_working_capital_kernels():
    # receivables = revenue * days / 365
    assert math.isclose(k("receivables", 365_000.0, 30.0), 30_000.0)
    assert math.isclose(k("inventory_days", 50.0, 365.0), 50.0)
    assert k("cash_conversion_cycle", 30.0, 40.0, 45.0) == 25.0
    assert k("working_capital", 100.0, 50.0, 40.0) == 110.0


def test_npv_matches_manual():
    # cf at t=0..2, r=10%: 100 + 110/1.1 + 121/1.21 = 100 + 100 + 100 = 300
    assert math.isclose(k("npv", 0.10, np.array([100.0, 110.0, 121.0])), 300.0, rel_tol=1e-9)


def test_irr_zero_npv():
    # cashflows -100, 60, 60 -> irr solves NPV=0
    irr = k("irr", np.array([-100.0, 60.0, 60.0]))
    npv_at_irr = k("npv", irr, np.array([-100.0, 60.0, 60.0]))
    assert abs(npv_at_irr) < 1e-4
    assert 0.1 < irr < 0.15


def test_future_and_present_value_inverse():
    fv = k("future_value", 0.05, 10, 0.0, -1000.0)
    pv = k("present_value", 0.05, 10, 0.0, -fv)
    assert math.isclose(pv, 1000.0, rel_tol=1e-6)


def test_risk_kernels():
    series = np.array([0.02, -0.01, 0.03, -0.04, 0.01])
    assert math.isclose(k("volatility", series), float(np.std(series)))
    assert math.isclose(k("variance", series), float(np.var(series)))
    # VaR at 0.8 is the negative of the 0.2 quantile
    assert math.isclose(k("var", series, 0.8), -float(np.quantile(series, 0.2)), rel_tol=1e-9)


def test_percentage_change():
    assert math.isclose(k("percentage_change", 100.0, 120.0), 0.20)
