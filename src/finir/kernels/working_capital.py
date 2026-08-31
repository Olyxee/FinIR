"""Working-capital kernels."""

from __future__ import annotations

from ..numerics import safe_div
from ..types import Days, Money, Scalar
from .registry import KernelRegistry, const_result, first_money_or_scalar


def register_all(reg: KernelRegistry) -> None:
    # receivables = revenue * days / 365
    reg.add(
        "receivables",
        lambda revenue, days: revenue * safe_div(days, 365.0),
        _money_result,
        arity=2,
        doc="revenue * receivable_days / 365",
    )
    reg.add(
        "payables",
        lambda cogs, days: cogs * safe_div(days, 365.0),
        _money_result,
        arity=2,
        doc="cogs * payable_days / 365",
    )
    reg.add(
        "inventory_days",
        lambda inventory, cogs: safe_div(inventory, cogs) * 365.0,
        const_result(Days()),
        arity=2,
        doc="inventory / cogs * 365",
    )
    reg.add(
        "cash_conversion_cycle",
        lambda dso, dio, dpo: dso + dio - dpo,
        const_result(Days()),
        arity=3,
        doc="days_sales_outstanding + days_inventory_outstanding - days_payable_outstanding",
    )
    reg.add(
        "working_capital",
        lambda receivables, inventory, payables: receivables + inventory - payables,
        first_money_or_scalar,
        arity=3,
        doc="receivables + inventory - payables",
    )
    reg.add(
        "working_capital_change",
        lambda wc_new, wc_old: wc_new - wc_old,
        first_money_or_scalar,
        arity=2,
        doc="working_capital_new - working_capital_old",
    )


def _money_result(arg_types):
    for t in arg_types:
        if isinstance(t, Money):
            return t
    return Scalar()
