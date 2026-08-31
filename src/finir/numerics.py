"""Safe numerical behaviour for financial computation (item 27).

Finance is unforgiving about silent division-by-zero, NaN, and infinity. FinIR
routes risky arithmetic through this module, governed by a configurable
:class:`NumericPolicy`. Vectorized workloads use float64 (documented precision
trade-off); a Decimal path is available for money-sensitive scalar computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Any

import numpy as np

from .exceptions import NumericError


@dataclass
class NumericPolicy:
    """How to handle risky numeric conditions."""

    on_div_zero: str = "nan"  # 'nan' | 'zero' | 'raise'
    on_nonfinite: str = "ignore"  # 'ignore' | 'raise'
    decimal_precision: int = 28


_POLICY = NumericPolicy()


def get_policy() -> NumericPolicy:
    return _POLICY


def set_policy(policy: NumericPolicy) -> None:
    global _POLICY
    _POLICY = policy
    getcontext().prec = policy.decimal_precision


def safe_div(a: Any, b: Any, policy: NumericPolicy | None = None) -> Any:
    """Divide with configured zero-handling; works for scalars and arrays."""
    p = policy or _POLICY
    a_arr = np.asarray(a, dtype="float64")
    b_arr = np.asarray(b, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.divide(a_arr, b_arr)
    zero_mask = b_arr == 0
    if np.any(zero_mask):
        if p.on_div_zero == "raise":
            raise NumericError("division by zero")
        fill = np.nan if p.on_div_zero == "nan" else 0.0
        out = np.where(zero_mask, fill, out)
    return _restore_scalar(out, a, b)


def check_finite(value: Any, policy: NumericPolicy | None = None, *, where: str = "value") -> Any:
    p = policy or _POLICY
    if p.on_nonfinite == "raise":
        arr = np.asarray(value, dtype="float64")
        if not np.all(np.isfinite(arr)):
            raise NumericError(f"non-finite value in {where}")
    return value


def _restore_scalar(out: np.ndarray, a: Any, b: Any) -> Any:
    if np.isscalar(a) and np.isscalar(b):
        return float(out)
    return out


def to_decimal(value: float) -> Decimal:
    """Convert a float to Decimal at the configured precision (money-sensitive scalar math)."""
    return Decimal(str(value))
