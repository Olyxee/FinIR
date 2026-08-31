"""FinIR benchmark harness (reusable by the CLI and the scripts in benchmarks/)."""

from __future__ import annotations

from .incremental import run_incremental_benchmark
from .scenario_bench import run_scenario_benchmark
from .synthetic import build_segmented_model, node_count

__all__ = [
    "build_segmented_model",
    "node_count",
    "run_incremental_benchmark",
    "run_scenario_benchmark",
]
