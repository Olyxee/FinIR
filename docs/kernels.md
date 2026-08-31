# Kernels

A kernel is a named finance-native operation with (a) a numeric implementation that
works on scalars and NumPy arrays, and (b) a type rule for the type-checker.
Arithmetic `+ - * /` are core IR operators; kernels cover the named primitives.

## Built-in kernels

**Arithmetic:** `add`, `subtract`, `multiply`, `divide`, `ratio`,
`percentage_change`, `growth`, `compound`, `discount`.

**Corporate:** `gross_profit`, `gross_margin`, `ebitda`, `ebitda_margin`,
`operating_margin`, `free_cash_flow`, `break_even`.

**Working capital:** `receivables`, `payables`, `inventory_days`,
`cash_conversion_cycle`, `working_capital`, `working_capital_change`.

**Time value of money:** `npv`, `irr`, `xirr`, `future_value`, `present_value`,
`annuity`.

**Risk:** `variance`, `volatility`, `var`, `cvar`, `drawdown`.

## Conventions

- **NPV**: `NPV = Σ_t cf[t] / (1+rate)^t`, with the first cashflow at `t=0`
  undiscounted. `npv(rate, cashflows)` takes a series (array) or explicit args.
- **IRR/XIRR**: solved by bisection over a sign-changing cashflow stream; `xirr`
  takes arbitrary year offsets.
- **VaR/CVaR**: historical, at a confidence `level` (default 0.95); returns the loss
  (positive number).
- Money-in → money-out kernels return the currency of their money argument; ratio
  kernels return `ratio`.

## Scope (honesty)

This is intentionally a **small** set — FinIR is not a quant library. It covers the
operations an AI system commonly needs; for deep instrument pricing, defer to a
dedicated library (e.g. QuantLib) and wrap what you need as a custom kernel.

## Custom kernels

```python
from finir import kernel
from finir.types import Money


@kernel("logistics.landed_cost", result=Money("ZAR"), arity=2)
def landed_cost(unit_cost, freight):
    return unit_cost + freight
```

Then use it in any expression: `landed = logistics.landed_cost(unit_cost, freight)`.
See [extending.md](extending.md).
