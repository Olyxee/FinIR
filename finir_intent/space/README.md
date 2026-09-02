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

Neither `finir` nor `finir-intent` is on PyPI yet. `requirements.txt` installs both
directly from GitHub (pip's VCS install syntax, which Hugging Face Spaces supports
natively) rather than waiting on a PyPI publish -- pinned to a commit SHA for
reproducibility, since it's a monorepo and both packages must stay in sync.
Verified end-to-end from a clean virtualenv (no local `sys.path` tricks, no bundled
source): `pip install -r requirements.txt` then running this Space's `app.py`
executes real instructions against the real FinIR runtime.

**Update the commit SHA in `requirements.txt`** after the PR merges to `main` (pin
to the merge commit, or to a release tag once one exists). `app.py`'s local
`sys.path` fallback still exists for running this Space straight out of a repo
checkout during development; it is never used once the package installs normally
from `requirements.txt`, as on Hugging Face.

Once `finir`/`finir-intent` are published to PyPI (see `docs/pypi-release.md` in
the core repo), swap these two lines for version-pinned PyPI requirements as the
more conventional long-term path -- not required for launch.
