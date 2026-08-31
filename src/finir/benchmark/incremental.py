"""Incremental-vs-full-recompute benchmark (items 22, 23).

Simulates an iterative agent: a base evaluation followed by many small single-input
changes. The two conditions run the *same* graph and kernels:

* **baseline** clears the cache each turn -> full recompute of every needed node.
* **finir** keeps the cache warm -> recomputes only the changed input's cone.

This isolates the value of dependency-aware incremental execution (identical
arithmetic, so the comparison is fair). Nothing is hard-coded — it times real runs.
"""

from __future__ import annotations

import time
from typing import Any

from .synthetic import build_segmented_model, input_names, node_count


def _time_workload(model, turns: int, *, incremental: bool) -> tuple[float, float]:
    """Return (total_seconds, cache_hit_ratio) for a base eval + ``turns`` changes."""
    engine = model._ensure_engine()
    inputs = input_names(model)
    all_nodes = [n for n in model.module.order]

    model.evaluate(targets=all_nodes)  # warm base
    engine.cache.reset_stats()

    start = time.perf_counter()
    for t in range(turns):
        name = inputs[t % len(inputs)]
        engine.set_input(name, 1_000_000 + (t + 1) * 137.0)
        if not incremental:
            engine.cache.clear()
        engine.evaluate(targets=all_nodes)
    elapsed = time.perf_counter() - start
    return elapsed, engine.cache.stats.hit_ratio


def run_incremental_benchmark(*, quick: bool = True) -> list[dict[str, Any]]:
    """Run the benchmark across a few model sizes; returns rows of metrics."""
    configs = (
        [(10, 3, 20), (40, 5, 40)]
        if quick
        else [(10, 3, 40), (40, 5, 60), (120, 6, 80), (300, 6, 100)]
    )
    rows: list[dict[str, Any]] = []
    for segments, depth, turns in configs:
        model = build_segmented_model(segments=segments, depth=depth)
        nodes = node_count(model)

        # Baseline (fresh model so no warm cache leaks between conditions).
        base_model = build_segmented_model(segments=segments, depth=depth)
        baseline_s, _ = _time_workload(base_model, turns, incremental=False)

        finir_s, hit_ratio = _time_workload(model, turns, incremental=True)
        rows.append(
            {
                "nodes": nodes,
                "turns": turns,
                "baseline_s": baseline_s,
                "finir_s": finir_s,
                "speedup": (baseline_s / finir_s) if finir_s > 0 else float("inf"),
                "cache_hit_ratio": hit_ratio,
            }
        )
    return rows
