"""Time-value-of-money kernels.

Convention: cashflow index ``t = 0, 1, ..., N-1`` with the first cashflow at ``t=0``
undiscounted, i.e. ``NPV = sum_t cf[t] / (1+rate)^t``. Documented in docs/kernels.md.
"""

from __future__ import annotations

import numpy as np

from ..types import Scalar
from .registry import KernelRegistry, const_result


def _npv(rate: float, *cashflows) -> float:
    cfs = _as_flow(cashflows)
    t = np.arange(len(cfs))
    return float(np.sum(cfs / np.power(1.0 + rate, t)))


def _as_flow(cashflows) -> np.ndarray:
    if len(cashflows) == 1 and np.ndim(cashflows[0]) >= 1:
        return np.asarray(cashflows[0], dtype="float64")
    return np.asarray(cashflows, dtype="float64")


def _irr(*cashflows) -> float:
    cfs = _as_flow(cashflows)
    # Bisection on rate in (-0.9999, 10). Requires a sign change in NPV.
    lo, hi = -0.9999, 10.0

    def npv_at(r: float) -> float:
        t = np.arange(len(cfs))
        return float(np.sum(cfs / np.power(1.0 + r, t)))

    f_lo, f_hi = npv_at(lo), npv_at(hi)
    if f_lo * f_hi > 0:
        return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = npv_at(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def _xirr(values, years) -> float:
    v = np.asarray(values, dtype="float64")
    yrs = np.asarray(years, dtype="float64")
    lo, hi = -0.9999, 10.0

    def npv_at(r: float) -> float:
        return float(np.sum(v / np.power(1.0 + r, yrs)))

    f_lo, f_hi = npv_at(lo), npv_at(hi)
    if f_lo * f_hi > 0:
        return float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = npv_at(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def _future_value(rate, nper, pmt, pv) -> float:
    r = float(rate)
    if r == 0:
        return -(float(pv) + float(pmt) * float(nper))
    factor = (1.0 + r) ** float(nper)
    return -(float(pv) * factor + float(pmt) * (factor - 1.0) / r)


def _present_value(rate, nper, pmt, fv) -> float:
    r = float(rate)
    if r == 0:
        return -(float(fv) + float(pmt) * float(nper))
    factor = (1.0 + r) ** float(nper)
    return -(float(fv) + float(pmt) * (factor - 1.0) / r) / factor


def _annuity_payment(rate, nper, pv) -> float:
    r = float(rate)
    if r == 0:
        return -float(pv) / float(nper)
    factor = (1.0 + r) ** float(nper)
    return -float(pv) * r * factor / (factor - 1.0)


def register_all(reg: KernelRegistry) -> None:
    reg.add("npv", _npv, const_result(Scalar()), doc="net present value; NPV = sum cf[t]/(1+r)^t")
    reg.add("irr", _irr, const_result(Scalar()), doc="internal rate of return (bisection)")
    reg.add("xirr", _xirr, const_result(Scalar()), arity=2, doc="irr with arbitrary year offsets")
    reg.add(
        "future_value",
        _future_value,
        const_result(Scalar()),
        arity=4,
        doc="future_value(rate, nper, pmt, pv)",
    )
    reg.add(
        "present_value",
        _present_value,
        const_result(Scalar()),
        arity=4,
        doc="present_value(rate, nper, pmt, fv)",
    )
    reg.add(
        "annuity",
        _annuity_payment,
        const_result(Scalar()),
        arity=3,
        doc="level annuity payment: annuity(rate, nper, pv)",
    )
