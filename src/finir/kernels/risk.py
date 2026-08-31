"""Basic risk kernels over a series of returns/values.

Deliberately small — FinIR is not a quant library. These cover the primitives an
AI system commonly needs when reasoning about a series of outcomes.
"""

from __future__ import annotations

import numpy as np

from ..types import Scalar
from .registry import KernelRegistry, const_result


def _variance(series) -> float:
    return float(np.var(np.asarray(series, dtype="float64")))


def _volatility(series) -> float:
    return float(np.std(np.asarray(series, dtype="float64")))


def _var(series, level=0.95) -> float:
    """Historical Value-at-Risk: the loss at the (1-level) quantile."""
    arr = np.asarray(series, dtype="float64")
    if arr.size == 0:
        return float("nan")
    q = np.quantile(arr, 1.0 - float(level))
    return float(-q)


def _cvar(series, level=0.95) -> float:
    """Conditional VaR (expected shortfall) beyond the VaR threshold."""
    arr = np.asarray(series, dtype="float64")
    if arr.size == 0:
        return float("nan")
    cutoff = np.quantile(arr, 1.0 - float(level))
    tail = arr[arr <= cutoff]
    if tail.size == 0:
        return float(-cutoff)
    return float(-tail.mean())


def _drawdown(series) -> float:
    """Maximum peak-to-trough drawdown of a cumulative value series (fraction)."""
    arr = np.asarray(series, dtype="float64")
    if arr.size == 0:
        return 0.0
    running_max = np.maximum.accumulate(arr)
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = np.where(running_max != 0, (arr - running_max) / running_max, 0.0)
    return float(-dd.min())


def register_all(reg: KernelRegistry) -> None:
    reg.add("variance", _variance, const_result(Scalar()), arity=1, doc="variance of a series")
    reg.add("volatility", _volatility, const_result(Scalar()), arity=1, doc="std dev of a series")
    reg.add(
        "var", _var, const_result(Scalar()), doc="historical Value-at-Risk (level default 0.95)"
    )
    reg.add("cvar", _cvar, const_result(Scalar()), doc="conditional VaR / expected shortfall")
    reg.add("drawdown", _drawdown, const_result(Scalar()), arity=1, doc="max drawdown fraction")
