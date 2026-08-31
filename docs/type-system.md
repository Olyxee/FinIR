# The finance-aware type system

Financial computation is unsafe when a system can silently add money to a day-count
or mix currencies. FinIR gives every value a type and enforces the algebra of
finance at compile time, so agent-generated computations fail loudly instead of
producing nonsense.

## Types

| Type | Textual | Meaning |
|------|---------|---------|
| `Money(currency)` | `money[ZAR]` | a currency amount |
| `Percentage` | `percentage` | a percentage/rate change (e.g. `4%` → 0.04) |
| `Ratio` | `ratio` | a dimensionless ratio (e.g. a margin) |
| `Days` | `days` | a day count |
| `Quantity(unit)` | `quantity[units]` | a count of things |
| `Rate(per)` | `rate[year]` | a per-period rate |
| `Boolean` | `bool` | a boolean |
| `Scalar` | `scalar` | a plain number |
| `Series(elem, period)` | `series[money[ZAR],month]` | a time series |
| `ScenarioVector(elem)` | `scenario[money[ZAR]]` | a batch across a scenario dim |

`Series` and `ScenarioVector` wrap an element type; arithmetic unwraps, applies the
element rule, and re-wraps.

## The algebra (selected rules)

```
money  - money   -> money      (same currency; else CurrencyError)
money  / money   -> ratio
money  * percentage -> money    (also ratio, scalar)
money  * money   -> TypeCheckError
money  + days    -> TypeCheckError
USD    + ZAR     -> CurrencyError
days   / scalar  -> days
scalar * scalar  -> scalar
```

Invalid operations raise `TypeCheckError`; currency mixing raises `CurrencyError`
(a subclass), pointing the user to an explicit conversion.

## Why this matters for AI

An agent that writes `revenue + receivable_days` or mixes USD and ZAR gets a clear
compile-time error instead of a silently wrong number — the type system is a guard
rail around generated financial computation.

## Currency conversion

Currencies never mix implicitly. Convert explicitly (see
[financial-semantics.md](financial-semantics.md)); a converted value carries the
target currency type.
