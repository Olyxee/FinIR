# FinIR — Hugging Face release staging

Export-ready content for three artifacts. **Nothing here is published**; this is a
staging area to review before publishing.

| directory | Hugging Face repo | type |
|---|---|---|
| `finir-intent/` | `Olyxee/FinIR-Intent` | model (deterministic baseline code + card) |
| `finir-intentbench/` | `Olyxee/FinIR-IntentBench` | dataset |
| `finir-space/` | Space (`Olyxee/FinIR-Intent-Demo`) | Gradio demo |

The canonical FinIR Intent Contract schema is **not** duplicated here — the core
`finir` package (https://pypi.org/project/finir/) is its single source of truth, as the cards state.

Compatibility: FinIR runtime `0.1.0` · Intent Contract `1.0` · FinIR-Intent baseline
`0.1.0` · FinIR-IntentBench `v1`.

Regenerate with `python finir_intent/scripts/build_release.py`.
