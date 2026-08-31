"""Working-capital template (uses working-capital kernels for correct typing)."""

from __future__ import annotations

from ..model import FinancialModel


def working_capital(model: FinancialModel) -> FinancialModel:
    """Given ``revenue``, ``cogs``, ``receivable_days``, ``payable_days``, ``inventory``,
    define receivables, payables, and net working capital.
    """
    model.define("receivables", "receivables(revenue, receivable_days)")
    model.define("payables", "payables(cogs, payable_days)")
    model.define("net_working_capital", "working_capital(receivables, inventory, payables)")
    return model
