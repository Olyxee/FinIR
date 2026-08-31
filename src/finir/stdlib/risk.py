"""Risk helpers built on the risk kernels."""

from __future__ import annotations

from ..model import FinancialModel


def return_risk(model: FinancialModel, *, series: str = "returns") -> FinancialModel:
    """Define volatility and drawdown over a ``returns`` series input."""
    model.define("volatility", f"volatility({series})")
    model.define("value_at_risk", f"var({series})")
    return model
