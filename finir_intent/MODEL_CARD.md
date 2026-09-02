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

The evaluation suite originally split FinIR-IntentBench into a `core` subset (the
phrasing this rule-based baseline is built to support) and a `stress` subset
(paraphrases deliberately outside its patterns, to surface real gaps). All five
gaps the `stress` subset originally found have since been fixed and moved into
`core` with regression coverage:

- Spelled-out numbers ("five percent", "five million rand") -- now parsed via a
  small, fixed number-word vocabulary (`_words_to_number`).
- The direction-word list (increase/decrease/grow/fall/...) previously missed
  "trim" -- fixed by adding `trim`/`trims` to the down-direction list.
- The target-alias table previously missed "supplier invoices" for
  `accounts_payable` -- added.
- `range` detection previously required `range`/`sweep`/`grid`/`scan` plus
  `from ... to ... N steps` -- widened to also accept `explore` plus
  `between ... and ... N points`.

The dataset currently has no `stress` (deliberately adversarial) examples left
unresolved -- see "Evaluation results" below. This does **not** mean the baseline
is complete: it is still a fixed rule set (a hand-authored alias table, a small
number-word vocabulary, keyword-anchored regexes), not a trained model, so any
phrasing outside what's enumerated in `src/finir_intent/baseline.py` still falls
back to `ambiguous` rather than being guessed. Growing FinIR-IntentBench with new
adversarial paraphrases (the same way the five above were found) is expected,
ongoing work, and the honest way to keep measuring this gap rather than hide it.

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
40 new examples, all now `core`-difficulty -- the 5 examples that previously
exposed real gaps, and the 8 `regression_*` examples added after a code review
found real word-boundary bugs, are both folded in; see "known limitations"). Full
per-example output, including every prediction and its execution outcome against
the real runtime: `eval/results/latest.json`. **Re-run the command above to
reproduce** -- do not trust this table without doing so if the code has changed
since.

| metric | value (n=49) |
|---|---|
| schema validity rate | 1.0000 |
| status accuracy | 1.0000 |
| operation accuracy | 1.0000 |
| target accuracy | 1.0000 |
| value accuracy | 1.0000 |
| unit accuracy | 1.0000 |
| currency accuracy (extra, not required) | 1.0000 |
| multi-operation accuracy (exact-match) | 1.0000 |
| ambiguity handling: precision / recall / F1 | 1.0000 / 1.0000 / 1.0000 |

Every one of the 49 examples is now `core`-difficulty (n=49, status accuracy
1.0000, schema validity 1.0000) -- there is no remaining `stress` subset. Every
example additionally executed successfully (or was correctly rejected, for the
`invalid` category) against the real FinIR runtime -- see the `execution` field
per example in `eval/results/latest.json`.

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
(`regression_*` ids). A fifth issue -- "trim" was missing from the down-direction
word list, so `"trim cogs by 4%"` produced the correct target and operation but the
wrong sign -- was found afterward and is now also fixed and regression-tested
(`test_trim_is_recognized_as_a_down_direction_word`, dataset id
`direction_word_trim`). All five are why every metric above is now 1.0000.

## License

Apache-2.0, matching the core FinIR repository.
