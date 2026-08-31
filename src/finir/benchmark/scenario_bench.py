"""Scenario-batch backend benchmark (items 23, 25).

Times vectorized-CPU (and, when present, GPU) execution of a scenario batch across
a range of sizes. Used to find the empirical crossover where GPU beats CPU, which
feeds the dispatch planner's threshold. GPU rows are produced only if a device is
actually available — never fabricated.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from ..backends.gpu import GpuBackend, gpu_available
from ..backends.numpy_backend import NumpyBackend
from .synthetic import build_segmented_model


def _time_batch(model, size: int, backend, repeats: int = 3) -> float:
    engine = model._ensure_engine()
    engine.backend = backend
    inputs = [i.name for i in model.module.inputs()]
    overrides = {inputs[0]: np.linspace(1e6, 2e6, size)}
    engine.evaluate(overrides=overrides, scenario_id=f"warm_{size}")  # warm
    best = float("inf")
    for _ in range(repeats):
        t0 = time.perf_counter()
        engine.evaluate(overrides=overrides, scenario_id=f"warm_{size}")
        best = min(best, time.perf_counter() - t0)
    return best


def run_scenario_benchmark(sizes: list[int] | None = None) -> dict[str, Any]:
    sizes = sizes or [1_000, 10_000, 100_000, 1_000_000]
    model = build_segmented_model(segments=10, depth=5)
    cpu = NumpyBackend()
    have_gpu = gpu_available()
    gpu = GpuBackend() if have_gpu else None

    rows = []
    for size in sizes:
        cpu_s = _time_batch(model, size, cpu)
        row: dict[str, Any] = {"size": size, "cpu_s": cpu_s, "gpu_s": None, "gpu_speedup": None}
        if gpu is not None:  # pragma: no cover - hardware dependent
            gpu_s = _time_batch(model, size, gpu)
            row["gpu_s"] = gpu_s
            row["gpu_speedup"] = cpu_s / gpu_s if gpu_s > 0 else None
        rows.append(row)
    return {"gpu_available": have_gpu, "rows": rows}
