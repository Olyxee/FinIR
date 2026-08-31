"""Reproduce Experiment 002 — backend dispatch thresholds.

Research question: at what scenario-batch size does GPU execution beat vectorized
CPU for finance-native computation graphs? We time CPU (always) and GPU (only if a
device is present) across batch sizes to locate the empirical crossover, which
feeds the dispatch planner's threshold.

    python research/reproduce_experiment_002.py

Writes research/results_002.json. GPU rows are produced ONLY on real hardware —
never fabricated.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from finir.benchmark import run_scenario_benchmark
from finir.version import __version__

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "research" / "results_002.json"


def main() -> None:
    sizes = [1_000, 10_000, 100_000, 1_000_000, 5_000_000]
    result = run_scenario_benchmark(sizes=sizes)

    # Determine the empirical CPU throughput curve; GPU crossover if measured.
    crossover = None
    for row in result["rows"]:
        if row["gpu_s"] is not None and row["gpu_speedup"] and row["gpu_speedup"] > 1.0:
            crossover = row["size"]
            break

    payload = {
        "hardware": {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "finir": __version__,
            "gpu_available": result["gpu_available"],
        },
        "research_question": (
            "At what scenario batch size does GPU beat vectorized CPU for finance graphs?"
        ),
        "rows": result["rows"],
        "empirical_gpu_crossover": crossover,
        "note": (
            "No CUDA device on this machine; GPU rows are null and the crossover is "
            "UNVERIFIED locally. The dispatch default (GPU_MIN_ELEMENTS) is a heuristic "
            "to be calibrated on GPU hardware."
        )
        if not result["gpu_available"]
        else "GPU measured; see crossover.",
    }
    RESULTS.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Experiment 002 — backend dispatch thresholds")
    print("=" * 46)
    print(f"gpu_available = {result['gpu_available']}")
    for r in result["rows"]:
        gpu = (
            "n/a (no device)"
            if r["gpu_s"] is None
            else f"{r['gpu_s']:.4f}s (x{r['gpu_speedup']:.2f})"
        )
        print(f"  size {r['size']:>9,}: cpu {r['cpu_s']:.5f}s  gpu {gpu}")
    if crossover:
        print(f"\nEmpirical GPU crossover: >= {crossover:,} scenarios")
    else:
        print("\nGPU crossover UNVERIFIED locally (no CUDA device).")
    print(f"Wrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
