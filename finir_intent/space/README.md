---
title: FinIR Intent
emoji: 📈
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.0.0"
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

`app.py` imports `finir_intent` from the sibling `../src` directory rather than
from PyPI, since this package is not yet published (see the workstream
`README.md` "Packaging note"). To deploy this as a real Hugging Face Space, either:

- publish `finir-intent` to PyPI and add it to `requirements.txt`, or
- copy `src/finir_intent/` into this directory before pushing to the Space repo.

This is a packaging/deployment detail for after local review, not a code change.
