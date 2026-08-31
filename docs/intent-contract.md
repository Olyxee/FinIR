# FinIR Intent Contract

- **FinIR Intent Schema:** `1.0`
- **Compatible FinIR Runtime:** `>=0.1.0,<0.2.0`
- **Canonical JSON Schema:** [`schemas/finir-intent-v1.schema.json`](../schemas/finir-intent-v1.schema.json) (byte-identical copy packaged at `finir/intent/finir-intent-v1.schema.json`)
- **Python types:** [`src/finir/intent/schema.py`](../src/finir/intent/schema.py)

This is the authoritative interface between a natural-language layer (which *emits*
the contract) and the FinIR runtime (which *consumes* it). It reflects exactly what
the runtime supports today — nothing is aspirational.

```
Natural-language financial intent → FinIR-Intent → Canonical Contract → FinIR Runtime
```

## Envelope

```json
{
  "schema_version": "1.0",
  "status": "valid",
  "operations": [
    { "operation": "relative_change", "target": "cogs", "value": 0.06 }
  ]
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `schema_version` | yes | Must be `"1.0"`. Identifies the compatibility contract. |
| `status` | yes | `valid` \| `ambiguous` \| `unsupported` \| `invalid`. |
| `reason` | no (recommended for non-valid) | Human-readable explanation. |
| `operations` | for operation intents | Array of operations, applied **simultaneously**. |
| `scenarios` | for scenario intents | Named scenarios. Mutually exclusive with a non-empty `operations`. |

### Status values

| status | meaning | executable? | operations/scenarios |
|--------|---------|-------------|----------------------|
| `valid` | Safe to execute. | yes | non-empty |
| `ambiguous` | Understandable but missing required quantitative detail. | no | must be empty |
| `unsupported` | Clear but FinIR cannot represent it as a model mutation. | no | must be empty |
| `invalid` | Structurally or semantically invalid. | no | must be empty |

A non-`valid` intent that carries operations or scenarios is itself rejected.

## Operations

| operation | semantics | required | optional |
|-----------|-----------|----------|----------|
| `relative_change` | `new = current × (1 + value)` | `target`, `value` | — (no unit/currency; dimensionless) |
| `set` | `new = value` | `target`, `value` | `unit`, `currency` |
| `absolute_change` | `new = current + value` | `target`, `value` | `unit`, `currency` |
| `range` | batch: set `target` to `steps` values evenly over `[min, max]` | `target`, `min`, `max`, `steps` | — |

**`relative_change` is multiplicative.** `{"operation":"relative_change","target":"revenue","value":-0.08}`
means `new_revenue = current_revenue × (1 − 0.08)` — **not** `current − 0.08`.

`absolute_change` maps to the runtime's additive change (internally `delta`). The
legacy operation names `change` (→ `relative_change`) and `delta` (→ `absolute_change`)
are accepted and normalized.

`range` is a vectorized batch (executed via `run_scenarios`); a `range` operation
must be the **only** operation in its intent and may not appear inside a scenario.

### Examples (executable)

```json
{ "operation": "set", "target": "payment_terms", "value": 60, "unit": "days" }
{ "operation": "absolute_change", "target": "opex", "value": 5000000, "currency": "ZAR" }
{ "operation": "range", "target": "cogs", "min": 300000000, "max": 400000000, "steps": 100 }
```

### Invalid examples

```json
{ "operation": "relative_change", "target": "cogs", "value": 0.04, "unit": "days" }   // dimensionless op may not carry a unit
{ "operation": "range", "target": "cogs", "min": 1, "max": 2, "steps": 3, "value": 9 } // range may not carry value
```

## Targets

`target` is the **name of a model input node** (e.g. `cogs`, `revenue`,
`payment_terms`). It is **not** a canonical financial ontology, and **FinIR resolves
no aliases** — `"sales"` is not mapped to `"revenue"` by the runtime. Any
alias/synonym handling belongs to the natural-language layer *before* it emits the
contract. Only model **inputs** can be targeted; targeting a computed node or an
unknown name makes the intent invalid at execution.

## Values, units, currency

- **relative_change** values are dimensionless decimals (`-0.08` = −8%).
- **set / absolute_change** values are numbers in the target's own unit. `unit` and
  `currency` are optional annotations.
- **Units** (`unit`) are one of `money`, `percentage`, `ratio`, `days`, `rate`,
  `quantity`, `scalar`, aligned with FinIR's type system.
- **Currency** (`currency`) is an ISO-4217 3-letter code. If omitted for a money
  target, the target's own currency is **inherited**. If present it **must equal**
  the target's currency — there is **no implicit FX conversion**; a mismatch makes
  the intent invalid at execution. FX conversion is expressed in the *model*, never
  as an intent.

> **Two validation levels.** The JSON Schema validates **structure** (model-free —
> this is what the NL layer runs). **Semantic** validation (target exists; unit and
> currency are compatible with the target's finance type) happens at execution
> against a *specific* model, inside `execute_intent` / `FinancialModel.apply_intent`.

## Period / time scope

Intents affect the **current scalar state** of an input only. FinIR supports series
inputs, but v1.0 intents do **not** carry period scoping (monthly/quarterly/annual/
specific-period). Do not emit period fields; they are not consumed.

## Multi-operation semantics

Operations in `operations` are applied **simultaneously** to the base state (they
are merged into one set of overrides). **Two operations on the same target are
invalid** — the contract rejects duplicate targets rather than silently ordering
them.

## Scenario semantics

```json
{
  "schema_version": "1.0",
  "status": "valid",
  "scenarios": [
    { "name": "base", "operations": [] },
    { "name": "upside", "operations": [ { "operation": "relative_change", "target": "revenue", "value": 0.10 } ] },
    { "name": "downside", "operations": [
        { "operation": "relative_change", "target": "revenue", "value": -0.08 },
        { "operation": "relative_change", "target": "cogs", "value": 0.05 } ] }
  ]
}
```

Each scenario's operations are simultaneous (same rules as above). Execution maps to
`FinancialModel.scenarios(...)` and returns one result per scenario name.

## Ambiguity, unsupported, invalid

- **Ambiguous** — vague quantities. *"Improve margins next year"*, *"grow sales
  significantly"*, *"reduce costs a little"* → `status: "ambiguous"`, `operations:
  []`. The layer must **never** invent a number.
- **Unsupported** — clear but not a model mutation. *"Acquire our largest
  competitor"* → `status: "unsupported"`.
- **Invalid** — structurally or semantically wrong: `revenue + 30 days`; *"set gross
  margin to R5 million"* (money value on a ratio, or a non-input target); *"increase
  ZAR revenue by USD 2 million"* (currency mismatch, no FX). These are rejected by
  the JSON Schema (structural) or by `execute_intent` (semantic).

## Versioning policy

| change | version bump | examples |
|--------|--------------|----------|
| **Patch** (runtime) | runtime patch only | validation-bug fix, doc clarification — no serialized-compatibility change |
| **Minor** schema (`1.1`) | backward-compatible | a new operation, a new optional field |
| **Major** schema (`2.0`) | breaking | a removed/renamed field, or **any change to operation semantics** |

Operation semantics are **never** silently altered. `schema_version` must match the
major/minor the runtime advertises; the runtime's compatibility range is stated at
the top of this document and in the handoff.

## Validation & execution

```python
from finir import FinancialModel
from finir.intent import FinIRIntent, execute_intent, json_schema

FinIRIntent.json_schema()  # the machine-readable contract (dict)
intent = FinIRIntent.from_obj(payload)  # structural validation (raises on error)
model.apply_intent(payload)  # normalize + validate (structural + semantic) + execute
```

Shared fixtures: [`tests/fixtures/intents/`](../tests/fixtures/intents). Contract
tests: [`tests/test_intent_contract.py`](../tests/test_intent_contract.py).
