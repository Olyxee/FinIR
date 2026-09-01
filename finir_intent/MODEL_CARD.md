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

## Purpose

FinIR-Intent turns a natural-language financial instruction into the **FinIR
Intent Contract** -- a canonical, versioned JSON envelope that the
[FinIR](https://github.com/Olyxee/finir) runtime validates and executes. It
performs **no financial computation**: interpretation and execution are strictly
separated (see `docs/agent-integration.md` in the core repo).

This is the **first-milestone baseline**: a deterministic, rule-based structured-
output compiler, not a trained model. Per the workstream brief: "the first
milestone is not model training... only after the baseline is measured should we
decide whether fine-tuning a small open model provides a meaningful improvement."
This baseline exists to make that measurement possible.

## What it is / is not

- **Is**: a small, dependency-free, fully offline pattern-matching compiler
  (`src/finir_intent/baseline.py`). No network access, no external LLM/API calls,
  fully reproducible.
- **Is not**: a trained language model. It implements the same `IntentCompiler`
  interface a future LLM-backed compiler would (`finir.intent.IntentCompiler`),
  so it is a drop-in baseline to compare against.

## Schema / runtime compatibility

- **FinIR Intent schema version:** `1.0`
- **Compatible FinIR runtime:** `>=0.1.0,<0.2.0`
- Canonical contract: owned by the core `finir` package
  (`finir.intent.json_schema()`, `schemas/finir-intent-v1.schema.json`). This
  package never redefines it.

## Supported intent categories

Revenue, COGS, opex, price, volume, payment terms, accounts payable, inventory,
capex, debt, interest rate, cash -- one raw model-input-node target each (no
canonical ontology; alias resolution happens only in this package, never in the
contract). Operations: `relative_change`, `set`, `absolute_change`, `range`, and
named `scenarios`. See `src/finir_intent/baseline.py` for the exact alias table
and phrasing patterns supported.

## Ambiguity / unsupported behavior

- Vague language (no target, or a target with no parseable quantity) -> `status:
  "ambiguous"`, empty operations. **No number is ever invented.**
- Conflicting operations on the same target in one instruction (e.g. "increase
  revenue by 5% and also cut revenue by 10%") -> `ambiguous` rather than silently
  picking one.
- Clearly out-of-domain requests (acquisitions, mergers, hiring/layoffs, IPOs,
  litigation, buybacks) -> `status: "unsupported"`.
- A structurally valid but semantically wrong instruction (e.g. a currency the
  target doesn't use) is **transcribed faithfully, never "corrected"** -- the real
  FinIR runtime rejects it at execution. This package never performs that
  semantic check itself (no duplicated execution logic).

## Known limitations (honestly measured, not hidden)

The evaluation suite splits FinIR-IntentBench into a `core` subset (the phrasing
this rule-based baseline is built to support) and a `stress` subset (paraphrases
deliberately outside its patterns, to surface real gaps). Confirmed failure modes
in the `stress` subset:

- Spelled-out numbers ("five percent", "five million rand") are not parsed --
  falls back to `ambiguous` rather than inventing a number, which is safe but
  under-recalls valid instructions.
- A handful of direction words are recognized (increase/decrease/grow/fall/...);
  a verb outside that list (e.g. "trim") does not flip the sign, so
  `stress_wrong_direction_verb` predicts the correct target and operation but the
  wrong sign.
- The target-alias table is a fixed, hand-authored list; a synonym outside it
  (e.g. "supplier invoices" for accounts payable) is not resolved.
- `range` detection requires an explicit trigger word (`range`/`sweep`/`grid`/
  `scan`) plus `from ... to ... N steps` phrasing.

These are exactly the gaps a future fine-tuned or LLM-backed compiler (behind the
same `IntentCompiler` interface) would need to close -- this baseline's job is to
make that gap measurable, not to hide it.

## Evaluation methodology

Reproduce with:

```bash
cd finir_intent
pip install -e ".[dev]"
python eval/evaluate.py -v
```

The suite (`eval/evaluate.py`) runs the baseline over every
`intentbench/examples/intentbench_v1.jsonl` example, checks the prediction against
`finir.intent.json_schema()` (the canonical schema), scores it against the paired
expected intent, and -- for every prediction the contract marks executable --
actually executes it against a small reference `FinancialModel`
(`finir_intent/reference_model.py`) via `finir.intent.execute_intent`, the real
runtime path (`finir.intent.execute_intent` / `FinancialModel.apply_intent`), with
no execution logic duplicated in this package.

## Evaluation results

Produced by an actual run of `python eval/evaluate.py` against
`intentbench/examples/intentbench_v1.jsonl` (n=49: the 9 shared canonical fixtures +
40 new examples, of which 5 are the deliberately out-of-pattern "stress" subset and
8 are regression tests added after a code review found real word-boundary bugs --
see "known limitations"). Full per-example output, including every prediction and
its execution outcome against the real runtime: `eval/results/latest.json`.
**Re-run the command above to reproduce** -- do not trust this table without doing
so if the code has changed since.

| metric | value (all, n=49) |
|---|---|
| schema validity rate | 1.0000 |
| status accuracy | 0.9184 |
| operation accuracy | 0.9091 |
| target accuracy | 0.9091 |
| value accuracy | 0.9750 |
| unit accuracy | 1.0000 |
| currency accuracy (extra, not required) | 1.0000 |
| multi-operation accuracy (exact-match) | 1.0000 |
| ambiguity handling: precision / recall / F1 | 0.7778 / 1.0000 / 0.8750 |

| subset | n | status accuracy | schema validity |
|---|---|---|---|
| `core` (curated, in-pattern) | 44 | 1.0000 | 1.0000 |
| `stress` (deliberate paraphrases, see "known limitations") | 5 | 0.2000 | 1.0000 |

All 4 status misclassifications and the ambiguity-handling false positives come
from the `stress` subset (the baseline correctly falling back to `ambiguous`
instead of guessing, on phrasing it can't parse -- safe, but under-recall). The
single `value_accuracy` miss is `stress_wrong_direction_verb` (sign only; operation
and target were still both correct). Every `core` example additionally executed
successfully (or was correctly rejected, for the `invalid` category) against the
real FinIR runtime -- see the `execution` field per example in
`eval/results/latest.json`.

### Fixed during review (previously silent, now regression-tested)

A code review after the initial implementation found that direction-word and
unsupported-word matching used plain substring checks instead of word boundaries,
causing real false positives on ordinary English: "up" inside "supplier"/"group"
flipped the sign of an otherwise-correct decrease; "merge" inside "emergency" and
"sue" inside "issue" misclassified valid, fully-quantified instructions as
`unsupported`. A related gap let `"set <money-target> to N%"` silently fall through
to `relative_change` (inventing a meaning the instruction never stated) instead of
refusing to guess. All four are fixed, covered by dedicated unit tests
(`tests/test_baseline.py`) and by 8 new `core`-difficulty dataset entries
(`regression_*` ids) so a regression would show up in both `pytest` and this table.

## License

Apache-2.0, matching the core FinIR repository.
