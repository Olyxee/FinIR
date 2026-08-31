"""Valuation helpers built on the TVM kernels."""

from __future__ import annotations

from ..model import FinancialModel


def dcf(
    model: FinancialModel, *, cashflow_series: str = "cashflows", rate: str = "discount_rate"
) -> FinancialModel:
    """Define ``enterprise_value = npv(discount_rate, cashflows)``.

    Expects a scalar input ``discount_rate`` and a series input ``cashflows``.
    """
    model.define("enterprise_value", f"npv({rate}, {cashflow_series})")
    return model
