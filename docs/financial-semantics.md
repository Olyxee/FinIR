# Financial semantics

FinIR understands common financial metrics and their computational dependencies —
but does **not** impose one universal accounting model. It gives you reusable
primitives (kernels) and templates (`finir.stdlib`) that you can override.

## Dependencies FinIR reasons about

```
Revenue ── COGS ─────────► Gross Profit ──► Gross Margin
                                  │
                                  └──► EBITDA ──► Operating Margin ──► Free Cash Flow

Revenue ──► Receivables ─┐
COGS    ──► Payables ─────┼──► Working Capital ──► Cash impact
Inventory ───────────────┘
```

These are relationships, not laws: redefine any node to change the model.

## Templates (`finir.stdlib`)

| Template | Adds |
|----------|------|
| `accounting.income_statement` | gross_profit, gross_margin, ebitda, operating_margin |
| `working_capital.working_capital` | receivables, payables, net_working_capital |
| `corporate.operating_model` | income statement + free_cash_flow |
| `valuation.dcf` | enterprise_value = npv(discount_rate, cashflows) |
| `risk.return_risk` | volatility, value_at_risk over a returns series |
| `unit_economics.saas` | lifetime_months, ltv, ltv_cac |

```python
from finir import FinancialModel
from finir.stdlib import accounting

m = FinancialModel()
m.input("revenue", 500e6, currency="ZAR")
m.input("cogs", 300e6, currency="ZAR")
m.input("opex", 120e6, currency="ZAR")
accounting.income_statement(m)  # defines the metrics for you
m.output("ebitda", "gross_margin")
```

## Currency

Currencies are typed (`money[ZAR]`, `money[USD]`) and never mix implicitly. Convert
explicitly — multiply a `money[ZAR]` value by a scalar FX rate and treat the result
as the target currency, or wrap an `fx_convert` custom kernel. The type system
(see [type-system.md](type-system.md)) rejects `USD + ZAR`.

## Time series & periods

`model.input_series(name, values, period="month")` declares a series input.
Operations preserve the element type; FinIR keeps a minimal internal representation
rather than reimplementing pandas.
