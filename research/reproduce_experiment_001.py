"""Reproduce Experiment 001 — multimodal evidence vs structured data alone.

Runs the two conditions over the synthetic benchmark suite and writes the
results to ``research/results_001.json``. Deterministic: same inputs -> same
numbers, every run.

    python research/reproduce_experiment_001.py

Hypothesis: adding text/document evidence to structured financial data detects
financially material events *earlier* (higher ESLT) and with *at least as good*
detection than structured data alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from eif.benchmark import generate_canonical, render_comparison_text, run_suite, suite_to_dict
from eif.config import Config

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "benchmarks" / "cases"
RESULTS = ROOT / "research" / "results_001.json"


def main() -> None:
    if not CASES.exists() or not any(CASES.glob("*/case.json")):
        generate_canonical(CASES)

    cfg = Config()

    baseline = run_suite(CASES, config=cfg, condition="baseline", structured_only=True)
    eif = run_suite(CASES, config=cfg, condition="eif")

    print(render_comparison_text(baseline, eif))
    print()

    payload = {
        "hypothesis": (
            "Multimodal business evidence identifies financially material events "
            "earlier and at least as accurately as structured financial data alone."
        ),
        "baseline": suite_to_dict(baseline),
        "eif": suite_to_dict(eif),
    }
    RESULTS.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
