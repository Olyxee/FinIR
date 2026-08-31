"""Corporate-finance kernels: margins, EBITDA, free cash flow, break-even."""

from __future__ import annotations

from ..numerics import safe_div
from ..types import Money, Ratio, Scalar
from .registry import KernelRegistry, const_result, first_money_or_scalar


def register_all(reg: KernelRegistry) -> None:
    reg.add(
        "gross_profit",
        lambda revenue, cogs: revenue - cogs,
        first_money_or_scalar,
        arity=2,
        doc="revenue - cogs",
    )
    reg.add(
        "gross_margin",
        lambda gross_profit, revenue: safe_div(gross_profit, revenue),
        const_result(Ratio()),
        arity=2,
        doc="gross_profit / revenue",
    )
    reg.add(
        "ebitda",
        lambda gross_profit, opex: gross_profit - opex,
        first_money_or_scalar,
        arity=2,
        doc="gross_profit - opex",
    )
    reg.add(
        "ebitda_margin",
        lambda ebitda, revenue: safe_div(ebitda, revenue),
        const_result(Ratio()),
        arity=2,
        doc="ebitda / revenue",
    )
    reg.add(
        "operating_margin",
        lambda operating_income, revenue: safe_div(operating_income, revenue),
        const_result(Ratio()),
        arity=2,
        doc="operating_income / revenue",
    )
    reg.add(
        "free_cash_flow",
        lambda ebitda, capex, tax, wc_change: ebitda - capex - tax - wc_change,
        first_money_or_scalar,
        arity=4,
        doc="ebitda - capex - tax - change_in_working_capital",
    )
    reg.add(
        "break_even",
        lambda fixed_costs, price, variable_cost: safe_div(fixed_costs, (price - variable_cost)),
        _breakeven_result,
        arity=3,
        doc="fixed_costs / (price - variable_cost)  -> units",
    )


def _breakeven_result(arg_types):
    # units to break even is a scalar quantity
    return Scalar()


_ = Money  # re-exported type used by callers/tests
