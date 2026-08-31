"""Run the FinIR benchmark suite and write results with hardware metadata.

    python benchmarks/run_benchmarks.py

Writes JSON to benchmarks/results/. Nothing is hard-coded — every number comes from
timing real execution on this machine.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from finir.benchmark import run_incremental_benchmark, run_scenario_benchmark
from finir.version import __version__

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def _hardware() -> dict:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "processor": platform.processor() or platform.machine(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "finir": __version__,
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    hw = _hardware()

    print("FinIR benchmarks on:", hw["platform"], "| python", hw["python"], "| numpy", hw["numpy"])

    incremental = run_incremental_benchmark(quick=False)
    scenario = run_scenario_benchmark()

    payload = {
        "hardware": hw,
        "incremental_vs_recompute": incremental,
        "scenario_backend": scenario,
    }
    out = RESULTS / "benchmark_results.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\nIncremental vs full recompute:")
    for r in incremental:
        print(
            f"  {r['nodes']:>5} nodes, {r['turns']:>3} turns: "
            f"baseline {r['baseline_s']:.4f}s  finir {r['finir_s']:.4f}s  "
            f"speedup {r['speedup']:.2f}x  cache_hit {r['cache_hit_ratio'] * 100:.1f}%"
        )

    print(f"\nScenario backend (gpu_available={scenario['gpu_available']}):")
    for r in scenario["rows"]:
        gpu = "n/a" if r["gpu_s"] is None else f"{r['gpu_s']:.4f}s"
        print(f"  size {r['size']:>9,}: cpu {r['cpu_s']:.4f}s  gpu {gpu}")

    print(f"\nWrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
