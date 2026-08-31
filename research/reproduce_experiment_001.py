"""Reproduce Experiment 001 — incremental financial reasoning.

Research question: can a finance-native IR with dependency-aware caching materially
reduce the compute cost of *iterative* financial reasoning by an AI system, vs.
full recomputation each turn?

    python research/reproduce_experiment_001.py

Writes research/results_001.json. Deterministic graph; timings are real.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from finir import FinancialModel
from finir.benchmark import run_incremental_benchmark
from finir.version import __version__

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "research" / "results_001.json"

# The realistic agent turn sequence (item 22), as (input, change-spec) pairs.
AGENT_TURNS = [
    ("revenue", "+5%"),
    ("revenue", "+8%"),
    ("cogs", "+3%"),
    ("receivable_days", "30d->60d"),
    ("opex", "-4%"),
]


def _company() -> FinancialModel:
    m = FinancialModel(name="company")
    m.input("revenue", 500_000_000, currency="ZAR")
    m.input("cogs", 300_000_000, currency="ZAR")
    m.input("opex", 120_000_000, currency="ZAR")
    m.input("receivable_days", 30, type="days")
    m.input("payable_days", 45, type="days")
    m.input("inventory", 50_000_000, currency="ZAR")
    m.define("gross_profit", "revenue - cogs")
    m.define("gross_margin", "gross_profit / revenue", output=True)
    m.define("ebitda", "gross_profit - opex", output=True)
    m.define("receivables", "receivables(revenue, receivable_days)")
    m.define("working_capital", "working_capital(receivables, inventory, payables)", output=True)
    m.define("payables", "payables(cogs, payable_days)")
    return m


def _agent_workload(*, incremental: bool, repeats: int = 200) -> dict:
    m = _company()
    engine = m._ensure_engine()
    all_nodes = list(m.module.order)
    m.evaluate(targets=all_nodes)
    engine.cache.reset_stats()

    start = time.perf_counter()
    recomputed_total = 0
    for _ in range(repeats):
        for name, spec in AGENT_TURNS:
            from finir.runtime.scenario import resolve_change

            engine.set_input(name, resolve_change(engine.input_value(name), spec))
            if not incremental:
                engine.cache.clear()
            r = engine.evaluate(targets=all_nodes)
            recomputed_total += r.stats.nodes_evaluated
    elapsed = time.perf_counter() - start
    return {
        "seconds": elapsed,
        "turns": repeats * len(AGENT_TURNS),
        "nodes_recomputed_total": recomputed_total,
        "cache_hit_ratio": engine.cache.stats.hit_ratio,
    }


def _hardware() -> dict:
    return {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "finir": __version__,
    }


def main() -> None:
    baseline = _agent_workload(incremental=False)
    finir = _agent_workload(incremental=True)
    speedup = baseline["seconds"] / finir["seconds"] if finir["seconds"] else float("inf")

    scaling = run_incremental_benchmark(quick=False)

    payload = {
        "hardware": _hardware(),
        "research_question": (
            "Does dependency-aware incremental execution reduce the compute cost of "
            "iterative financial reasoning vs. full recomputation each turn?"
        ),
        "agent_workload": {
            "turn_sequence": AGENT_TURNS,
            "baseline_full_recompute": baseline,
            "finir_incremental": finir,
            "speedup": speedup,
            "recompute_reduction": 1.0
            - finir["nodes_recomputed_total"] / baseline["nodes_recomputed_total"],
        },
        "scaling": scaling,
    }
    RESULTS.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Experiment 001 — incremental financial reasoning")
    print("=" * 52)
    print(f"Agent workload ({finir['turns']} turns):")
    print(
        f"  baseline full recompute: {baseline['seconds']:.4f}s, "
        f"{baseline['nodes_recomputed_total']:,} node-recomputes"
    )
    print(
        f"  finir incremental      : {finir['seconds']:.4f}s, "
        f"{finir['nodes_recomputed_total']:,} node-recomputes, "
        f"cache_hit {finir['cache_hit_ratio'] * 100:.1f}%"
    )
    print(f"  speedup                : {speedup:.2f}x")
    print(
        f"  recompute reduction    : {payload['agent_workload']['recompute_reduction'] * 100:.1f}%"
    )
    print("\nScaling (nodes -> speedup):")
    for r in scaling:
        print(
            f"  {r['nodes']:>5} nodes: {r['speedup']:.2f}x  (cache_hit {r['cache_hit_ratio'] * 100:.1f}%)"
        )
    print(f"\nWrote {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
