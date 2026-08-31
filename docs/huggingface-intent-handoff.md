# FinIR Intent — Hugging Face handoff

**For:** Alisha (FinIR-Intent / natural-language → FinIR layer)
**From:** FinIR core runtime
**Schema:** `1.0` · **Compatible runtime:** `>=0.1.0,<0.2.0`

This is the current, authoritative contract — not a proposal. Your model must emit
exactly this envelope; the runtime validates and executes it. The full spec is
[intent-contract.md](intent-contract.md); this page is the implementation summary.

## 1. What FinIR-Intent is responsible for

Turn a natural-language financial request into **one canonical JSON envelope** that
validates against `schemas/finir-intent-v1.schema.json`. You own interpretation and
disambiguation (including any synonym/alias mapping to model input names). You do
**not** run any financial math.

## 2. What it must never do

- **Never invent numbers.** Vague input → `status: "ambiguous"`, empty operations.
- **Never emit an operation for a non-financial request.** → `status: "unsupported"`.
- **Never mix currencies or units.** No implicit FX; no `money + days`.
- **Never emit duplicate targets** in one `operations` list.
- **Never add fields the runtime does not consume** (e.g. period scoping).

## 3. Canonical schema

```json
{
  "schema_version": "1.0",
  "status": "valid | ambiguous | unsupported | invalid",
  "reason": "optional string (recommended for non-valid)",
  "operations": [ /* Operation, ... */ ],
  "scenarios":  [ /* { "name": "...", "operations": [ ... ] } */ ]
}
```
`operations` and `scenarios` are mutually exclusive (one non-empty at a time).
Machine-readable: `python -c "import finir.intent,json;print(json.dumps(finir.intent.json_schema()))"`.

## 4. Supported operations

| operation | meaning | fields |
|-----------|---------|--------|
| `relative_change` | `new = current × (1 + value)` | `target`, `value` (dimensionless) |
| `set` | `new = value` | `target`, `value`, opt `unit`/`currency` |
| `absolute_change` | `new = current + value` | `target`, `value`, opt `unit`/`currency` |
| `range` | batch of `steps` values over `[min,max]` | `target`, `min`, `max`, `steps` (sole op) |

`value: -0.08` under `relative_change` = **−8%**, i.e. `× 0.92` (not `− 0.08`).

## 5. Target / value / unit / currency semantics

- **target** = a model **input node name** (`revenue`, `cogs`, `opex`,
  `payment_terms`, …). No alias resolution in the runtime — map synonyms yourself.
- **value** = number in the target's unit; for `relative_change`, a dimensionless
  decimal.
- **unit** ∈ `money, percentage, ratio, days, rate, quantity, scalar` — optional,
  must be compatible with the target's type.
- **currency** = ISO-4217 (e.g. `ZAR`). Omit → inherits the target's currency.
  Present → must equal it (no FX). Mismatch = invalid at execution.

## 6. Ambiguity behavior

```json
{ "schema_version": "1.0", "status": "ambiguous",
  "reason": "No quantitative margin target was specified.", "operations": [] }
```
Use for: *"Improve margins next year."*, *"Sales should grow significantly."*,
*"Reduce costs a little."*, *"Make EBITDA better."*

## 7. Unsupported behavior

```json
{ "schema_version": "1.0", "status": "unsupported",
  "reason": "Cannot be represented as a FinIR model mutation.", "operations": [] }
```
Use for: *"Acquire our largest competitor."* Distinct from ambiguous: unsupported =
clear intent, wrong domain; ambiguous = right domain, missing quantity.

## 8. Version compatibility

Emit `"schema_version": "1.0"`. The runtime accepts `>=0.1.0,<0.2.0`. Minor schema
bumps (`1.1`) are additive and backward-compatible; a major bump (`2.0`) is breaking
and coordinated. Operation semantics never change silently.

## 9. Validation command

Structural (what you run in CI — model-free):

```python
import json, jsonschema, finir.intent

jsonschema.Draft202012Validator(finir.intent.json_schema()).validate(payload)
# or, using the runtime types:
from finir.intent import FinIRIntent

FinIRIntent.from_obj(payload)  # raises IntentValidationError on structural problems
```

Semantic + execution (needs a model):

```python
model.apply_intent(payload)  # structural + semantic validation, then executes
```

## 10. Example inputs and outputs

| natural language | envelope (abridged) |
|---|---|
| "COGS +4%" | `{status:valid, operations:[{relative_change, cogs, 0.04}]}` |
| "Revenue falls 8%, COGS rises 4%" | `{status:valid, operations:[{relative_change,revenue,-0.08},{relative_change,cogs,0.04}]}` |
| "Extend payment terms to 60 days" | `{status:valid, operations:[{set, payment_terms, 60, unit:days}]}` |
| "Increase opex by R5,000,000" | `{status:valid, operations:[{absolute_change, opex, 5000000, currency:ZAR}]}` |
| "Improve margins" | `{status:ambiguous, operations:[]}` |
| "Acquire a competitor" | `{status:unsupported, operations:[]}` |

Executed COGS +4% (input → runtime):

```json
{ "schema_version": "1.0", "status": "valid",
  "operations": [ { "operation": "relative_change", "target": "cogs", "value": 0.04 } ] }
```
→ `model.apply_intent(payload)` returns an `EvaluationResult`; `cogs` and its
downstream nodes recompute, the rest are reused.

## 11. Integration test instructions

```bash
pip install -e ".[dev]"
pytest tests/test_intent_contract.py -q
```
This validates every fixture against the JSON Schema and runs each through
`apply_intent` end to end (valid ones execute; ambiguous/unsupported/invalid raise
`IntentValidationError`).

## 12. Shared fixtures

`tests/fixtures/intents/` — the canonical inputs both workstreams depend on:

```
valid_relative_change.json   valid_absolute_change.json   valid_set_days.json
valid_multi_operation.json   valid_scenario.json
ambiguous_missing_value.json unsupported_operation.json
invalid_currency.json        invalid_type.json
```
Add new fixtures here when we agree new cases; both sides consume the same files.

## 13. How schema changes are coordinated

The JSON Schema and the Python types are one source of truth in this repo
(`schemas/finir-intent-v1.schema.json` == the packaged copy; a test enforces
no drift). To change the contract: open a PR editing the schema + `finir/intent/
schema.py` together, bump `schema_version` per the policy in
[intent-contract.md](intent-contract.md#versioning-policy), update fixtures, and tag
both workstreams. Never change operation semantics under the same version.

## Open items to confirm with the team

See the "contract decisions requiring agreement" section in the delivery notes —
chiefly: whether `range` stays in v1.0, and whether we add a small canonical
alias/target-map layer (currently **no** aliases; targets are raw input names).
