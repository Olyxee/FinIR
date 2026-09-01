---
license: apache-2.0
language: en
tags:
  - finance
  - structured-generation
  - finir
---

# Dataset Card: FinIR-IntentBench v1

## Purpose

Paired `{natural-language finance instruction, expected FinIR Intent}` examples
for evaluating any FinIR-Intent compiler (rule-based baseline, fine-tuned model, or
LLM-backed) against the canonical **FinIR Intent Contract** (schema `1.0`, owned by
the core `finir` package -- `finir.intent.json_schema()` /
`schemas/finir-intent-v1.schema.json`).

## Foundation: the shared canonical fixtures

9 of the 41 examples (`id` prefixed `canon_`) are the exact fixtures at
`tests/fixtures/intents/` in the core FinIR repo -- the same files
`tests/test_intent_contract.py` validates and executes on the runtime side. This
dataset resolves them by filename (the `fixture` field) rather than re-typing
their JSON, so the two workstreams can never drift apart on these cases. A natural-
language instruction was authored for each, matching its documented semantics.

## Format

One JSON object per line in `examples/intentbench_v1.jsonl`:

```json
{"id": "...", "category": "...", "difficulty": "core|stress", "text": "...",
 "expected_intent": { ... }}
```

or, for the 9 canonical examples:

```json
{"id": "canon_...", "category": "...", "difficulty": "core", "text": "...",
 "fixture": "valid_relative_change.json"}
```

An example whose `expected_intent` is structurally `"valid"` but semantically
wrong for the reference model (a currency or unit mismatch) carries
`"execution_expectation": "semantic_reject"` -- the evaluation suite checks that
executing it against the reference model correctly raises
`finir.intent.IntentValidationError`, proving the natural-language layer
transcribes faithfully and lets the *runtime* catch the semantic error (never
"fixing" it upstream).

## Categories

| category | count | covers |
|---|---|---|
| `valid_simple` | 22 | one operation: `relative_change` / `set` / `absolute_change` across every supported target (revenue, cogs, opex, price, volume, payment_terms, accounts_payable, inventory, capex, debt, interest_rate, cash) |
| `multi_operation` | 4 | multiple simultaneous operations in one instruction |
| `ambiguous` | 8 | vague quantities, no target, conflicting duplicate-target requests, or a "set to N%" on a non-percentage target |
| `unsupported` | 7 | clear but not a FinIR model mutation (acquisitions, IPOs, layoffs, litigation, hiring, bankruptcy) |
| `invalid` | 3 | structurally valid, semantically wrong at execution (currency or unit mismatch) |
| `range` | 3 | a `range` batch sweep (2 core phrasings + 1 stress paraphrase) |
| `scenario` | 2 | named `scenarios`, each with simultaneous operations |

(49 total: 9 shared canonical fixtures + 40 new examples, of which 5 are the
`stress` subset and 8 are `regression_*` cases added after a review found real
word-boundary bugs in the baseline -- see `../MODEL_CARD.md` "known limitations".)

`difficulty`: `core` (44 examples) is phrasing the baseline is built to support;
`stress` (5 examples) is deliberately outside its patterns -- spelled-out numbers,
an unrecognized direction verb, an unlisted target alias, and range phrasing
without a trigger word -- included so the evaluation suite reports real,
measured limitations rather than only the cases the baseline was tuned on. See
`../MODEL_CARD.md` "known limitations".

## What is *not* in this dataset

- No `period`/time-scope field anywhere (forbidden by the v1.0 contract).
- No private company data, no data from any real financial system.
- No canonical alias ontology is asserted -- targets are the raw FinIR
  model-input names used by `finir_intent/reference_model.py`; the mapping from
  natural-language synonyms to those names is the *compiler's* job, not the
  dataset's or the contract's.

## Versioning

Filename-versioned (`intentbench_v1.jsonl`). A breaking change to the FinIR Intent
Contract (a `schema_version` major bump) requires a new IntentBench major version
alongside it, per `docs/intent-contract.md#versioning-policy` in the core repo.
Additive cases can be appended to the same file without a version bump.

## License

Apache-2.0, matching the core FinIR repository. Entirely synthetic; no real
company or personal data.
