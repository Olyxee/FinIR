---
license: apache-2.0
language: en
tags:
  - finance
  - structured-generation
  - rule-based
  - finir
---

# Model Card: FinIR-Intent (baseline v0.1.0)

**This is a deterministic structured-output baseline, not a trained language model.**
It maps a natural-language financial instruction to the canonical **FinIR Intent
Contract** (a versioned JSON envelope) using a fixed, fully offline rule set. There
are no neural weights in this repository.

## What FinIR is

[FinIR](https://github.com/Olyxee/finir) is a financial intermediate representation
and incremental execution runtime for AI systems: a finance-typed computation graph
that is validated, compiled, and evaluated with dependency-aware incremental reuse.
It is published on PyPI (`pip install finir`, runtime `0.1.0`).

## What FinIR-Intent is

FinIR-Intent is the natural-language layer:

```
natural-language financial request  ->  FinIR-Intent  ->  canonical FinIR Intent Contract (v1.0)
```

It performs **no financial computation**. Interpretation and execution are strictly
separated: FinIR-Intent only produces the envelope; the FinIR runtime validates and
executes it (`finir.intent.execute_intent` / `FinancialModel.apply_intent`).

## The problem it solves

Letting an AI system "just compute" a financial what-if invites silently invented
numbers and unit/currency errors. FinIR-Intent constrains the language model's job
to emitting a **typed, validated intent**; the runtime is the single authority on
whether that intent is executable and what it computes. Vague language becomes an
explicit `ambiguous` status instead of a fabricated percentage.

## What it is / is not

- **Is**: a small, dependency-free, offline pattern-matching compiler
  (`src/finir_intent/baseline.py`) — no network, no external LLM/API calls, fully
  reproducible. It implements the same `finir.intent.IntentCompiler` seam a future
  LLM-backed compiler would, so it is a drop-in baseline to measure against.
- **Is not**: a trained/fine-tuned Transformer. Per the workstream brief, "the first
  milestone is not model training… only after the baseline is measured should we
  decide whether fine-tuning a small open model provides a meaningful improvement."
  This baseline exists to make that measurement possible.

## Hugging Face artifact type

Because v0.1.0 ships **code, not weights**, the natural representation is a
**model repository that contains the baseline package plus this card** — a
code/inference repo, not a weight checkpoint. The companion benchmark ships as a
**Datasets** repo, and a **Space** demonstrates the end-to-end flow against the real
runtime. The page makes explicit that this is a baseline compiler, not neural
weights. (See `../release/huggingface/` for the export layout.)

## Schema / runtime compatibility

- **FinIR Intent schema version:** `1.0`
- **Compatible FinIR runtime:** `>=0.1.0,<0.2.0` (verified against the public PyPI
  `finir==0.1.0`)
- **FinIR-Intent baseline version:** `0.1.0`
- The canonical contract is owned by the core `finir` package
  (`finir.intent.json_schema()`, `schemas/finir-intent-v1.schema.json`). This
  package **consumes** it and never redefines it.

## Supported operations

| operation | meaning |
|---|---|
| `relative_change` | `new = current × (1 + value)` (dimensionless decimal; `-0.08` = −8%) |
| `set` | `new = value` (with optional `unit` / `currency`) |
| `absolute_change` | `new = current + value` (with optional `unit` / `currency`) |
| `range` | sweep `target` over `[min, max]` in `steps` (sole op) |
| `scenarios` | named scenarios, each a simultaneous operation set |

## Supported targets

Raw model-input node names (no canonical ontology; alias resolution happens in this
package only, never in the contract): `revenue`, `cogs`, `opex`, `payment_terms`,
`accounts_payable`, `inventory`, `capex`, `debt`, `interest_rate`, `cash`, `price`,
`volume`.

## Ambiguity / unsupported / invalid behavior

- **Ambiguous** — a target with no parseable quantity, or vague language → `status:
  "ambiguous"`, empty operations. **No number is ever invented.** Conflicting
  operations on one target (e.g. "increase revenue by 5% and also cut revenue by
  10%") also map to `ambiguous` rather than silently picking one.
- **Unsupported** — clearly out-of-domain (acquisitions, mergers, hiring/layoffs,
  IPOs/going public, litigation, buybacks, bankruptcy) → `status: "unsupported"`.
- **Invalid (semantic)** — a structurally valid but semantically wrong instruction
  (a currency the target does not use, a `days` unit on a money target) is
  **transcribed faithfully, never "corrected"**; the FinIR runtime rejects it at
  execution. This package performs no semantic check itself (no duplicated execution
  logic).

## Evaluation methodology

Reproduce (deterministic; no network, no LLM):

```bash
pip install finir==0.1.0
cd finir_intent
pip install -e ".[dev]"        # or: PYTHONPATH=src, plus jsonschema
python eval/evaluate.py        # writes eval/results/latest.json
```

`eval/evaluate.py` runs the baseline over every
`intentbench/examples/intentbench_v1.jsonl` example, validates each prediction
against `finir.intent.json_schema()` (the canonical schema), scores it against the
paired **ground-truth** expected intent, and — for every executable prediction —
actually executes it against a small reference `FinancialModel`
(`src/finir_intent/reference_model.py`) via the real `finir.intent.execute_intent`.
Every number below is computed from that run; none is hand-typed.

### Benchmark split (anti-leakage)

FinIR-IntentBench is split into **core** (in-distribution phrasing the rule set is
built to support) and a held-out **stress** subset (paraphrases the baseline was
**not** tuned against — unlisted verbs, fractions, magnitude suffixes, idioms). The
baseline was deliberately **not** modified to pass stress cases, so the stress
numbers are an honest measure of the rule set's real coverage gap, not a tuned
score.

## Evaluation results

Produced by an actual run of `python eval/evaluate.py` on
`intentbench_v1.jsonl` (183 examples: 143 core, 40 stress). Full per-example output,
including every prediction and its execution outcome against the real runtime, is in
`eval/results/latest.json`. **Re-run the command above to reproduce** if the code has
changed.

| metric | overall (n=183) | core (n=143) | stress (n=40) |
|---|---|---|---|
| schema validity | 1.0000 | 1.0000 | 1.0000 |
| status accuracy | 0.9344 | 1.0000 | 0.7000 |
| operation accuracy | 0.9515 | 1.0000 | 0.7500 |
| target accuracy | 0.9515 | 1.0000 | 0.7500 |
| value accuracy | 0.9363 | 1.0000 | 0.5833 |
| unit accuracy | 1.0000 | 1.0000 | 1.0000 |
| currency accuracy | 1.0000 | 1.0000 | 1.0000 |
| ambiguity precision | 0.8409 | 1.0000 | 0.5333 |
| ambiguity recall | 0.9737 | 1.0000 | 0.8889 |
| ambiguity F1 | 0.9024 | 1.0000 | 0.6666 |
| multi-operation exact-match | 0.9000 | 1.0000 | 0.0000 |
| scenario exact-match | 1.0000 | 1.0000 | n/a |
| runtime execution success (executable preds) | 1.0000 | 1.0000 | 1.0000 |
| semantic-rejection correctness | 1.0000 | 1.0000 | 1.0000 |

**Do not read the overall numbers as a headline score.** They are a blend of a
saturated core set and a deliberately hard stress set. The core row shows what the
baseline reliably does; the stress row shows where a fixed rule set breaks.

## Known failure cases (from the stress subset)

Every current stress failure is one of two kinds — and **11 of 12 are conservative
refusals, never an invented number**:

- **Refuses (safe):** `valid → ambiguous` on phrasing outside the rule set —
  fractions/idioms ("Reduce COGS by a fifth", "Double the unit price", "Halve
  inventory"), an unlisted-target reference ("Increase AP by R2,000,000", "Reduce
  the wage bill by 6%"), and an unlisted additive idiom ("Add R5,000,000 to opex").
- **Refuses (safe):** `unsupported → ambiguous` on out-of-domain phrasing the
  vocabulary does not list ("Spin off the retail division", "Issue new equity",
  "Relocate the head office", "Replace the CEO").
- **Value errors (status still valid):** an unlisted direction verb defaults the
  sign to positive ("Slash opex by 12%" is parsed as +12%), and a magnitude suffix
  on a digit is not expanded ("Increase opex by R5m" is parsed as R5, not R5m).
- **The one genuinely unsafe failure:** "Grow cogs by 4% but also reduce cogs by 2%"
  is parsed as a single +4% change because `but also` is not a clause separator, so
  the conflicting second operation is dropped instead of triggering `ambiguous`.
  This is the only stress case where the baseline commits to a number it should have
  refused; it is tracked for a future fix.

## Limitations

This is a fixed rule set — a hand-authored alias table, a small number-word
vocabulary, keyword-anchored regexes — **not** a trained model. Any phrasing outside
what is enumerated in `src/finir_intent/baseline.py` falls back to `ambiguous`
rather than being guessed. It does not handle: fractional/idiomatic magnitudes ("a
fifth", "double", "halve"), magnitude suffixes on digits (`R5m`, `$2m`, `R1.2bn`),
unlisted direction verbs (slash/shave/ramp/shrink…), unlisted target aliases,
period/time scoping (forbidden by the v1.0 contract), or conflicting operations
joined by connectives other than `and`/`,`/`;`. Growing FinIR-IntentBench with new
adversarial paraphrases (as the stress subset does) is the honest way to keep
measuring this gap rather than hide it.

## Fixed parser issues (regression-tested)

- **Word-boundary matching** for direction and unsupported words: naive substring
  checks previously false-positived on ordinary English ("up" inside
  "supplier"/"group" flipped a decrease's sign; "merge" inside "emergency" and "sue"
  inside "issue" misclassified valid instructions as `unsupported`).
- **`set <money-target> to N%`** now refuses (`ambiguous`) instead of silently
  becoming a relative change.
- **Spelled-out numbers** ("five percent", "five million rand") parse via a small
  fixed number-word vocabulary.
- **`trim`/`trims`** added to the down-direction words ("trim cogs by 4 percent" →
  −4%).
- **`boost`/`boosts`, `raises`** added to the up-direction words.
- **Layoff/going-public phrasings with a number or filler between the trigger
  words** ("fire 100 employees", "take the company public") are now correctly
  `unsupported`, anchored to headcount/listing nouns so "fire up the pipeline" is not
  a false positive.

All are covered by unit tests in `tests/test_baseline.py` and by dataset entries.

## License

Apache-2.0, matching the core FinIR repository. The benchmark is entirely synthetic;
no real company or personal data.

## Repository & dependency

- Source & docs: https://github.com/Olyxee/finir (workstream under `finir_intent/`)
- Runtime dependency: `finir>=0.1.0,<0.2.0` — `pip install finir`
- Intent Contract spec: `docs/intent-contract.md`, `docs/huggingface-intent-handoff.md`

## Attribution

The FinIR-Intent Hugging Face workstream (baseline, benchmark, evaluation, Space) was
contributed by **Alisha Fatima** ([@AlishaFatima16](https://github.com/AlishaFatima16)).
The core FinIR runtime and the canonical FinIR Intent Contract are maintained by
Olyxee.


## Links

- **FinIR runtime (PyPI):** https://pypi.org/project/finir/ — `pip install finir`
- **FinIR source (GitHub):** https://github.com/Olyxee/finir
- **FinIR-IntentBench (dataset):** https://huggingface.co/datasets/Olyxee/FinIR-IntentBench
- **FinIR Space (demo):** https://huggingface.co/spaces/Olyxee/FinIR-Intent-Demo
