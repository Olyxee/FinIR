"""Income-statement template."""

from __future__ import annotations

from ..model import FinancialModel


def income_statement(model: FinancialModel) -> FinancialModel:
    """Given inputs ``revenue``, ``cogs``, ``opex``, define the income statement.

    Adds: gross_profit, gross_margin, ebitda, operating_margin.
    """
    model.define("gross_profit", "revenue - cogs")
    model.define("gross_margin", "gross_profit / revenue")
    model.define("ebitda", "gross_profit - opex")
    model.define("operating_margin", "ebitda / revenue")
    return model
