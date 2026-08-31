"""Core arithmetic kernels."""

from __future__ import annotations

import numpy as np

from ..numerics import safe_div
from ..types import FinType, Percentage, Ratio, Scalar
from .registry import KernelRegistry, const_result, first_money_or_scalar, same_as_first


def register_all(reg: KernelRegistry) -> None:
    reg.add("add", lambda a, b: a + b, same_as_first, arity=2, doc="a + b")
    reg.add("subtract", lambda a, b: a - b, same_as_first, arity=2, doc="a - b")
    reg.add("multiply", lambda a, b: a * b, first_money_or_scalar, arity=2, doc="a * b")
    reg.add("divide", safe_div, _div_result, arity=2, doc="a / b (safe)")
    reg.add("ratio", safe_div, const_result(Ratio()), arity=2, doc="a / b as a ratio")
    reg.add(
        "percentage_change",
        lambda old, new: safe_div(new - old, old),
        const_result(Percentage()),
        arity=2,
        doc="(new - old) / old",
    )
    reg.add(
        "growth",
        lambda base, rate: base * (1.0 + rate),
        same_as_first,
        arity=2,
        doc="base * (1 + rate)",
    )
    reg.add(
        "compound",
        lambda base, rate, periods: base * np.power(1.0 + rate, periods),
        same_as_first,
        arity=3,
        doc="base * (1 + rate) ** periods",
    )
    reg.add(
        "discount",
        lambda amount, rate, periods: safe_div(amount, np.power(1.0 + rate, periods)),
        same_as_first,
        arity=3,
        doc="amount / (1 + rate) ** periods",
    )


def _div_result(arg_types: list[FinType]) -> FinType:
    from ..types import binary_result

    if len(arg_types) == 2:
        return binary_result("/", arg_types[0], arg_types[1])
    return Scalar()
