# Impact Estimation

EIF estimates financial consequences with **arithmetic in code**, never by asking
a model "what is the impact?". This keeps numbers reproducible, auditable, and
free of hallucination.

## How it works

`DeterministicImpactEstimator.estimate(event, observations)`:

1. Pools the measurements available to the event (its own observations plus
   entity-less "context" observations — e.g. a spend table).
2. Looks up the event type's **impact strategy**.
3. Runs that strategy, which searches for the specific inputs it needs.
4. If the inputs are present, computes the number and records a `Calculation`.
   **If they are absent, it returns no impact** — the event is still stored, just
   without a fabricated figure.

## Strategies

| Strategy | Needs | Computes |
|----------|-------|----------|
| `spend_pct` | a percentage + a spend base | `spend * pct / 100` (e.g. COGS exposure) |
| `revenue_run_rate` | a percentage + a revenue base | `revenue * pct / 100` |
| `fixed_amount` | a stated amount | the amount directly (penalty, obligation, …) |
| `delay_cost` | one or more stated cost figures | a point + range from the figures |
| `inventory_delta` | a percentage + an inventory value | `value * pct / 100` |
| `generic` | any stated money amount | the amount, else nothing |

Example — supplier price increase:

```
Supplier announces +10%.  Annual spend = R42,000,000.
gross exposure = 42,000,000 * 10 / 100 = R4,200,000
```

## Uncertainty

Each impact is an `Estimate` with `point`, `lower`, `upper`, `unit`,
`probability`, and `confidence`. Interval width reflects input quality (narrower
when a deterministic calculation grounds the number, wider for stated ranges). See
[confidence.md](confidence.md).

## Where the model may help

A model may determine *applicability* (which products, which effective period),
introduce *assumptions* (recorded in provenance), or classify direction — but the
final arithmetic is always Python. Add your own strategy by subclassing
`ImpactEstimator` or adding a `_strategy_<name>` method and pointing an event type
at it via `impact_strategy`.
