# FinIR-Intent

The Hugging Face workstream of [FinIR](https://github.com/Olyxee/finir): natural-language
financial instructions in, a validated **FinIR Intent Contract** envelope out. This
package never runs financial math itself -- the core `finir` runtime does that.

```
"Increase COGS by 4%"  ->  FinIR-Intent  ->  { canonical envelope }  ->  finir runtime  ->  result
```

- **Canonical contract:** defined and owned by the core `finir` package
  (`finir.intent`, `schemas/finir-intent-v1.schema.json`). This package consumes it,
  it does not redefine it. See `../docs/intent-contract.md` and
  `../docs/huggingface-intent-handoff.md` in the FinIR repo.
- **Schema version:** `1.0` · **Compatible FinIR runtime:** `>=0.1.0,<0.2.0`

## Contents

| Path | What |
|---|---|
| `src/finir_intent/baseline.py` | The deterministic, rule-based FinIR-Intent baseline (no LLM, no network) |
| `src/finir_intent/reference_model.py` | A small demo `FinancialModel` covering every target the baseline names, for end-to-end proof and the Space |
| `intentbench/` | **FinIR-IntentBench** -- the paired instruction/expected-intent benchmark dataset and its dataset card |
| `eval/evaluate.py` | The reproducible evaluation suite |
| `space/` | The minimal Hugging Face Space (Gradio) |
| `MODEL_CARD.md` | Model card for the baseline |
| `tests/` | Unit + contract-reuse tests for this package |

## Quickstart

```bash
pip install -e .[dev]                 # from this directory; also needs the finir core package
python -m pytest tests/ -q
python eval/evaluate.py               # reproduces the evaluation results in MODEL_CARD.md
python space/app.py                   # launches the local Gradio demo
```

## Design boundary

- FinIR-Intent **interprets**; FinIR **executes**. This package never computes a
  financial result -- see `src/finir_intent/baseline.py` and
  `docs/agent-integration.md` in the core repo.
- FinIR-Intent never invents a number for vague language. Ambiguous input stays
  `status: "ambiguous"`, with empty operations.
- No alias resolution happens inside the contract. Synonym -> canonical target-name
  mapping (e.g. "sales" -> `revenue`) lives entirely in `baseline.py`, before the
  envelope is emitted -- exactly as `docs/intent-contract.md` requires.

## Packaging

Standalone, independently installable package `finir-intent` (import path
`finir_intent`), depending on the published `finir` runtime from PyPI
(`finir>=0.1.0,<0.2.0`). Versions: FinIR-Intent baseline `0.1.0`, FinIR-IntentBench
`v1`, Intent Contract `1.0`.

## Attribution

The FinIR-Intent Hugging Face workstream (baseline, benchmark, evaluation, Space)
was contributed by **Alisha Fatima** ([@AlishaFatima16](https://github.com/AlishaFatima16)).
The core FinIR runtime and the canonical Intent Contract are maintained by Olyxee.
