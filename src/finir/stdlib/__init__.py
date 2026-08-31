"""FinIR financial standard library (item 30).

Reusable primitives and templates that assemble common financial relationships on a
:class:`~finir.model.FinancialModel`. These are *starting points*, not a mandated
accounting model — every relationship can be overridden by redefining the node.

Namespaces:
    accounting      income statement
    corporate       operating model (income statement + FCF)
    working_capital receivables / payables / working capital
    valuation       NPV / DCF helpers
    risk            volatility / drawdown over a series
    unit_economics  SaaS LTV / CAC
"""

from __future__ import annotations

from . import accounting, corporate, risk, unit_economics, valuation, working_capital

__all__ = ["accounting", "corporate", "risk", "unit_economics", "valuation", "working_capital"]
