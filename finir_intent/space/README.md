---
title: FinIR Intent
emoji: 📈
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.50.0"
python_version: "3.12"
app_file: app.py
pinned: false
license: apache-2.0
---

# FinIR-Intent Space

Natural-language financial instruction -> **FinIR Intent Contract** (schema `1.0`)
-> validated -> executed by the real [FinIR](https://github.com/Olyxee/finir) runtime
(compatible range `>=0.1.0,<0.2.0`).

This Space contains **no financial computation of its own**. It calls:

1. `finir_intent.compile_intent` -- the deterministic, offline FinIR-Intent baseline
   (interpretation only).
2. `finir.intent.FinIRIntent.from_obj` -- structural validation against the
   canonical, versioned JSON Schema.
3. `finir.intent.execute_intent` (via `FinancialModel.apply_intent`) -- real
   execution against a small reference model (`finir_intent.reference_model`).

Ambiguous or unsupported instructions are refused, not guessed -- see
`../MODEL_CARD.md`.

## Packaging note

The FinIR runtime is on PyPI, so `requirements.txt` installs **`finir==0.1.0`
directly from PyPI** — the Space executes against exactly the package end users get
from `pip install finir`. `finir-intent` (this workstream) is not yet published, so
it is installed from GitHub (pip's VCS syntax, supported natively by Hugging Face
Spaces), pinned to a commit SHA for reproducibility.

**Publish-time step:** bump the `finir-intent` commit SHA in `requirements.txt` to
the commit that lands the v0.1.0 readiness work before deploying, then — once
`finir-intent` is published to PyPI — replace that line with `finir-intent==0.1.0`.
`app.py`'s local `sys.path` fallback exists only for running this Space straight out
of a repo checkout during development; it is never used once the package installs
normally from `requirements.txt`, as on Hugging Face.
