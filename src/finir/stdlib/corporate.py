"""Operating-model template: income statement + a simple free-cash-flow bridge."""

from __future__ import annotations

from ..model import FinancialModel
from .accounting import income_statement


def operating_model(model: FinancialModel) -> FinancialModel:
    """Income statement plus a free-cash-flow bridge.

    Expects inputs ``revenue``, ``cogs``, ``opex``, ``capex``, ``tax``,
    ``wc_change`` (change in working capital).
    """
    income_statement(model)
    model.define("free_cash_flow", "free_cash_flow(ebitda, capex, tax, wc_change)")
    return model
