#!/usr/bin/env python3
"""Build clean, export-ready Hugging Face publication directories.

Deterministic and repo-relative (no absolute paths). Produces, at the repo root:

  release/huggingface/
    README.md                      -- index of the three artifacts
    finir-intent/                  -- MODEL repo (baseline code + model card as README)
    finir-intentbench/             -- DATASET repo (inlined JSONL + splits + card)
    finir-space/                   -- SPACE (app + requirements + card)

Nothing is published; this only stages local files for review. The canonical Intent
Contract schema is NOT copied here: the core ``finir`` package remains its single
source of truth (the cards say so explicitly).

    python finir_intent/scripts/build_release.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WS = REPO / "finir_intent"
FIXTURES = REPO / "tests" / "fixtures" / "intents"
OUT = REPO / "release" / "huggingface"

GH = "https://github.com/Olyxee/finir"
PYPI = "https://pypi.org/project/finir/"
HF_MODEL = "https://huggingface.co/Olyxee/FinIR-Intent"
HF_DATA = "https://huggingface.co/datasets/Olyxee/FinIR-IntentBench"
HF_SPACE = "https://huggingface.co/spaces/Olyxee/FinIR-Intent-Demo"


def rm(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)


def inline_dataset() -> tuple[list[dict], list[dict], list[dict]]:
    """Resolve fixture refs inline and JSON-stringify expected_intent for a flat,
    stable Datasets schema. Returns (all, core, stress)."""
    src = WS / "intentbench" / "examples" / "intentbench_v1.jsonl"
    rows = []
    for ln in src.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if "fixture" in r:
            r["expected_intent"] = json.loads((FIXTURES / r["fixture"]).read_text(encoding="utf-8"))
            r.pop("fixture", None)
        rows.append(
            {
                "id": r["id"],
                "category": r["category"],
                "difficulty": r.get("difficulty", "core"),
                "text": r["text"],
                "execution_expectation": r.get("execution_expectation", ""),
                "expected_intent": json.dumps(r["expected_intent"], ensure_ascii=False),
            }
        )
    core = [r for r in rows if r["difficulty"] == "core"]
    stress = [r for r in rows if r["difficulty"] == "stress"]
    return rows, core, stress


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )


def main() -> None:
    rm(OUT)
    OUT.mkdir(parents=True)

    # ---- finir-intent (model repo) ------------------------------------------------
    mi = OUT / "finir-intent"
    (mi / "src").mkdir(parents=True)
    shutil.copytree(
        WS / "src" / "finir_intent",
        mi / "src" / "finir_intent",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(WS / "pyproject.toml", mi / "pyproject.toml")
    card = (WS / "MODEL_CARD.md").read_text(encoding="utf-8")
    links = f"""

## Links

- **FinIR runtime (PyPI):** {PYPI} — `pip install finir`
- **FinIR source (GitHub):** {GH}
- **FinIR-IntentBench (dataset):** {HF_DATA}
- **FinIR Space (demo):** {HF_SPACE}
"""
    (mi / "README.md").write_text(card + links, encoding="utf-8")

    # ---- finir-intentbench (dataset repo) -----------------------------------------
    di = OUT / "finir-intentbench"
    all_rows, core, stress = inline_dataset()
    write_jsonl(di / "data" / "intentbench_v1.jsonl", all_rows)
    write_jsonl(di / "data" / "core.jsonl", core)
    write_jsonl(di / "data" / "stress.jsonl", stress)
    dcard = (WS / "intentbench" / "DATASET_CARD.md").read_text(encoding="utf-8")
    fm_extra = (
        "configs:\n"
        "  - config_name: default\n"
        "    data_files:\n"
        "      - split: core\n"
        "        path: data/core.jsonl\n"
        "      - split: stress\n"
        "        path: data/stress.jsonl\n"
    )
    if dcard.startswith("---\n"):
        end = dcard.index("\n---", 4)
        dcard = dcard[:end] + "\n" + fm_extra + dcard[end:]
    cfg = f"""
## Files

- `data/intentbench_v1.jsonl` — all 183 examples (each `expected_intent` is a JSON string).
- `data/core.jsonl` — 143 core examples.
- `data/stress.jsonl` — 40 held-out stress examples.

## Links

- **FinIR-Intent (model/baseline):** {HF_MODEL}
- **FinIR source (GitHub):** {GH}
- **Intent Contract spec:** {GH}/blob/main/docs/intent-contract.md
"""
    (di / "README.md").write_text(dcard + cfg, encoding="utf-8")

    # ---- finir-space --------------------------------------------------------------
    si = OUT / "finir-space"
    si.mkdir(parents=True)
    shutil.copy2(WS / "space" / "app.py", si / "app.py")
    shutil.copy2(WS / "space" / "requirements.txt", si / "requirements.txt")
    scard = (WS / "space" / "README.md").read_text(encoding="utf-8")
    slinks = f"""

## Links

- **FinIR runtime (PyPI):** {PYPI}
- **FinIR source (GitHub):** {GH}
- **FinIR-Intent (model/baseline):** {HF_MODEL}
- **FinIR-IntentBench (dataset):** {HF_DATA}
"""
    (si / "README.md").write_text(scard + slinks, encoding="utf-8")

    # ---- index --------------------------------------------------------------------
    (OUT / "README.md").write_text(
        f"""# FinIR — Hugging Face release staging

Export-ready content for three artifacts. **Nothing here is published**; this is a
staging area to review before publishing.

| directory | Hugging Face repo | type |
|---|---|---|
| `finir-intent/` | `Olyxee/FinIR-Intent` | model (deterministic baseline code + card) |
| `finir-intentbench/` | `Olyxee/FinIR-IntentBench` | dataset |
| `finir-space/` | Space (`Olyxee/FinIR-Intent-Demo`) | Gradio demo |

The canonical FinIR Intent Contract schema is **not** duplicated here — the core
`finir` package ({PYPI}) is its single source of truth, as the cards state.

Compatibility: FinIR runtime `0.1.0` · Intent Contract `1.0` · FinIR-Intent baseline
`0.1.0` · FinIR-IntentBench `v1`.

Regenerate with `python finir_intent/scripts/build_release.py`.
""",
        encoding="utf-8",
    )

    n_files = sum(1 for _ in OUT.rglob("*") if _.is_file())
    print(f"wrote {OUT}")
    print(f"  files: {n_files}")
    print(f"  dataset: all={len(all_rows)} core={len(core)} stress={len(stress)}")


if __name__ == "__main__":
    main()
