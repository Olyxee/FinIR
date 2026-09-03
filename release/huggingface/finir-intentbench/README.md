---
license: apache-2.0
language: en
tags:
  - finance
  - structured-generation
  - finir
task_categories:
  - text-generation
pretty_name: FinIR-IntentBench
configs:
  - config_name: default
    data_files:
      - split: core
        path: data/core.jsonl
      - split: stress
        path: data/stress.jsonl

---

# Dataset Card: FinIR-IntentBench v1

## Purpose

Paired `{natural-language finance instruction, expected FinIR Intent}` examples for
evaluating any FinIR-Intent compiler (the rule-based baseline, a fine-tuned model, or
an LLM-backed one) against the canonical **FinIR Intent Contract** (schema `1.0`,
owned by the core `finir` package — `finir.intent.json_schema()` /
`schemas/finir-intent-v1.schema.json`, runtime `>=0.1.0,<0.2.0`).

## Size and splits

- **183 examples total.**
- **`core` (143)** — in-distribution phrasing the deterministic baseline is built to
  support.
- **`stress` (40)** — a held-out subset of harder paraphrases (unlisted verbs,
  fractions, magnitude suffixes, idioms, out-of-domain phrasing) authored
  **independently of the baseline's rules**. The baseline was deliberately not tuned
  to these; they exist so evaluation reports a real coverage gap rather than a score
  the parser was fitted to. See the split methodology below and `../MODEL_CARD.md`.

The `difficulty` field on every row records the split.

## Categories

| category | total | core | stress | covers |
|---|---|---|---|---|
| `valid_simple` | 118 | 90 | 28 | one operation (`relative_change` / `set` / `absolute_change`) across every supported target |
| `ambiguous` | 21 | 16 | 5 | vague quantities, no target, conflicting duplicate targets, "set to N%" on a non-percentage target |
| `unsupported` | 17 | 13 | 4 | clear but not a FinIR model mutation (acquisitions, IPOs/going public, layoffs, litigation, hiring, bankruptcy, spin-offs) |
| `multi_operation` | 10 | 9 | 1 | multiple simultaneous operations in one instruction |
| `invalid` | 7 | 5 | 2 | structurally valid, semantically wrong at execution (currency or unit mismatch) |
| `range` | 6 | 6 | 0 | a `range` batch sweep |
| `scenario` | 4 | 4 | 0 | named `scenarios`, each with simultaneous operations |

Every one of the 12 supported targets (`revenue`, `cogs`, `opex`, `payment_terms`,
`accounts_payable`, `inventory`, `capex`, `debt`, `interest_rate`, `cash`, `price`,
`volume`) and every operation type (`set`, `relative_change`, `absolute_change`,
`range`, multi-operation, `scenarios`), unit (`money`, `percentage`, `days`,
`quantity`) and currency (`ZAR`, `USD`) appears in the dataset.

## Format

One JSON object per line in `examples/intentbench_v1.jsonl`:

```json
{"id": "...", "category": "...", "difficulty": "core|stress", "text": "...",
 "expected_intent": { ...canonical FinIR Intent envelope... }}
```

9 examples (`id` prefixed `canon_`) instead carry a `fixture` field naming a file in
the core repo's `tests/fixtures/intents/` — the exact fixtures
`tests/test_intent_contract.py` validates and executes on the runtime side. The repo
copy references them by filename (rather than re-typing their JSON) so the benchmark
and the runtime can never drift apart on those cases; the **Hugging Face export**
(`../release/huggingface/finir-intentbench/`) resolves them inline so the dataset
loads with no dependency on the GitHub repo (see "Loading" below).

Seven rows whose `expected_intent` is structurally `"valid"` but semantically wrong
for the reference model carry `"execution_expectation": "semantic_reject"` — the
evaluation checks the runtime correctly raises `finir.intent.IntentValidationError`,
proving the NL layer transcribes faithfully and lets the runtime catch the error.

## Loading (Hugging Face Datasets)

The Hugging Face export ships fully inlined JSONL (no `fixture` references; the
`expected_intent` is a JSON string to keep a stable, flat schema), plus per-split
files:

```python
from datasets import load_dataset

ds = load_dataset("Olyxee/FinIR-IntentBench")  # 'core' and 'stress' splits
core = load_dataset("Olyxee/FinIR-IntentBench", split="core")

import json

row = core[0]
expected = json.loads(row["expected_intent"])  # the canonical envelope
```

No clone of the FinIR GitHub repo is required to use the dataset.

## Generation methodology

- **Fully synthetic.** No real company data, no data from any real financial system.
  All values are illustrative and generic.
- Ground-truth expected intents are derived from a structured spec (target,
  operation, direction, magnitude) — **not** by running the baseline parser — so the
  benchmark measures the parser rather than being defined by it (`../` generator in
  the workstream; see `../MODEL_CARD.md`).
- The 9 `canon_*` rows reuse the core repo's shared fixtures verbatim.
- **Human-reviewed:** every row was reviewed for a correct canonical envelope and
  correct split label; the core subset is additionally gated by a test asserting the
  baseline reaches 100% status accuracy on it, and every expected intent is checked
  against the canonical JSON Schema in CI.

## Split methodology (anti-leakage)

`core` is phrasing inside the documented rule set; `stress` is held-out paraphrases
authored to fall outside it. A benchmark hand-tuned until the parser passes every
case measures nothing — so the baseline is frozen against the stress subset. On the
current baseline the stress subset scores well below core (status 0.70 vs 1.00, value
0.58 vs 1.00), which is the intended, honest signal. When a stress case is genuinely
fixed in the rule set, it may move to `core` with regression coverage; new
adversarial paraphrases are added to `stress` to keep the gap measurable.

## What is not in this dataset

- No `period`/time-scope field (forbidden by the v1.0 contract).
- No private company, customer, or personal data — entirely synthetic.
- No canonical alias ontology: targets are the raw FinIR model-input names; synonym →
  target mapping is the compiler's job, not the dataset's or the contract's.

## Versioning

Filename-versioned (`intentbench_v1.jsonl`). A breaking change to the FinIR Intent
Contract (a `schema_version` major bump) requires a new IntentBench major version, per
`docs/intent-contract.md#versioning-policy`. Additive cases can be appended without a
version bump.

## License & attribution

Apache-2.0, matching the core FinIR repository. FinIR-IntentBench was contributed by
**Alisha Fatima** ([@AlishaFatima16](https://github.com/AlishaFatima16)) as part of
the FinIR-Intent Hugging Face workstream; the canonical contract it targets is
maintained by Olyxee.

## Files

- `data/intentbench_v1.jsonl` — all 183 examples (each `expected_intent` is a JSON string).
- `data/core.jsonl` — 143 core examples.
- `data/stress.jsonl` — 40 held-out stress examples.

## Links

- **FinIR-Intent (model/baseline):** https://huggingface.co/Olyxee/FinIR-Intent
- **FinIR source (GitHub):** https://github.com/Olyxee/finir
- **Intent Contract spec:** https://github.com/Olyxee/finir/blob/main/docs/intent-contract.md
