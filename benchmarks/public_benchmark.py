#!/usr/bin/env python3
"""FinIR public-package benchmark: incremental execution vs. full recomputation.

Benchmarks the **public PyPI `finir==0.1.0`** package only (this script asserts its
own import comes from an installed site-packages copy, never this repo's local
``src/finir``, and records the exact file path used). It does not modify FinIR core
in any way -- it is a new, standalone script built entirely on the public
``finir.FinancialModel`` API (``.input``, ``.define``, ``.set``, ``.evaluate``,
``.dirty_nodes``), plus one private accessor (``model._ensure_engine()``) used only
to read back internal dependency-graph structure for a correctness check, never to
change behavior.

Three benchmarks, run against synthetic financial models (clearly labeled synthetic
throughout -- not real company data):

  A. incremental_vs_full   -- across graph sizes, one changed input, at each size:
                               median incremental vs. full-recompute time, speedup,
                               recomputed/reused node counts.
  B. change_locality       -- at a fixed graph size, vary the percentage of inputs
                               changed simultaneously (1/5/10/25/50/100%).
  C. cold_warm_update      -- at a fixed graph size: cold (first-ever) evaluation,
                               warm no-op repeat, a small (1-input) update, and a
                               larger (50%-input) update.

Synthetic graph shape (this script's own generator, not FinIR's shipped
``finir.benchmark.synthetic.build_segmented_model``): ``segments`` independent
depth-``5`` arithmetic chains, combined by a *balanced* pairwise-sum binary tree
(not one flat N-ary sum). This is a deliberate, documented deviation from the
shipped generator: a flat ``"a + b + c + ..."`` aggregate over >~1,000 segments
recurses once per term in FinIR's expression-AST walker (``finir.ir.expr.free_refs``)
and hits Python's default recursion limit -- a real, reproducible constraint of that
helper at this graph shape, not a defect worth patching core just to run a
benchmark. The balanced-tree aggregate reaches the same target node counts with
every single node's own expression staying shallow (one binary op), sidestepping the
limit entirely while remaining a realistic model shape (hierarchical business-unit
consolidation).

Methodology (see also the printed/embedded "methodology" block in the output JSON):

  * Fixed seed (``SEED = 42``) for every random choice (which inputs change).
  * Hardware, OS, Python, NumPy, and FinIR versions recorded in the output.
  * The *timed region* is exactly one ``model.evaluate()`` call. Model construction,
    the initial "warm" evaluation, and ``model.set(...)`` calls are all untimed setup
    -- construction time is reported separately, never mixed into execution time.
  * Full recomputation is modeled by building a **fresh, never-evaluated** model with
    the changed input value(s) already supplied at construction time, then timing its
    first ``evaluate()``. This needs no private "clear cache" call: a fresh model has
    nothing cached, so its first evaluate() is unambiguously a full recompute -- and
    it is directly comparable because it is the exact same graph, kernels, and
    backend as the incremental condition, just never warmed.
  * Incremental recomputation is modeled by building a model, evaluating it once
    (untimed warm-up), then applying the same input change(s) and timing the next
    ``evaluate()`` -- FinIR's dependency-aware dirty-set propagation recomputes only
    the changed cone and reuses everything else.
  * Each row is repeated ``REPS`` times (fresh model pair per repetition) and the
    median is reported as the primary statistic, alongside min/max.
  * Every row's incremental and full-recompute outputs are compared
    (``math.isclose``, rtol=1e-9) before being accepted; a mismatch aborts the run
    rather than being silently reported.
  * One representative case additionally cross-checks that the engine's reported
    ``recomputed`` node set matches ``model.dirty_nodes(...)`` (the actual dependency
    graph's transitive-dependents computation), independently confirming the
    reuse/recompute accounting is not just a plausible-looking number.

Run:

    python benchmarks/public_benchmark.py

Writes ``benchmarks/results/finir_public_benchmark_<date>.json`` and a flattened
``.csv`` of the same rows.
"""

from __future__ import annotations

import csv
import json
import math
import platform
import random
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

import finir
from finir import FinancialModel

SEED = 42
DEPTH = 5  # fixed chain depth per segment for every graph in this benchmark
ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
RUN_DATE = datetime.now(UTC).strftime("%Y-%m-%d")

# ----------------------------------------------------------------------- provenance
# Hard assertion, not a comment: refuse to run against a local/editable FinIR -- only
# an installed site-packages copy (i.e. what `pip install finir==0.1.0` gives a user)
# counts as "the public package" for this benchmark.
_FINIR_FILE = Path(finir.__file__).resolve()
_IS_SITE_PACKAGES = "site-packages" in str(_FINIR_FILE).replace("\\", "/")
if not _IS_SITE_PACKAGES:
    raise SystemExit(
        f"Refusing to run: finir imported from {_FINIR_FILE} does not look like an "
        "installed site-packages copy. This benchmark must run against the public "
        "PyPI package (pip install finir==0.1.0), not local/editable repo source."
    )


# --------------------------------------------------------------------------- graphs
def build_graph(
    segments: int, depth: int, *, overrides: dict[str, float] | None = None
) -> tuple[FinancialModel, str, list[str]]:
    """A synthetic financial model: ``segments`` independent depth-``depth`` chains
    combined by a balanced pairwise-sum binary tree. Returns (model, root_node_name,
    list_of_input_names). Built entirely on the public FinancialModel API.

    ``overrides`` supplies a starting value for specific input names instead of the
    default -- used to construct the "full recompute" condition's model with the
    changed value(s) already baked in at construction time (so no post-construction
    ``.set()`` + cache-clear is ever needed).
    """
    overrides = overrides or {}
    model = FinancialModel(name=f"bench_{segments}x{depth}")
    inputs: list[str] = []
    tails: list[str] = []
    for s in range(segments):
        base_name = f"s{s}_in"
        base_value = overrides.get(base_name, 1_000_000.0 + s)
        model.input(base_name, base_value, currency="ZAR")
        inputs.append(base_name)
        prev = base_name
        for d in range(depth):
            node = f"s{s}_n{d}"
            if d % 2 == 0:
                model.define(node, f"{prev} * 1.05")
            else:
                model.define(node, f"{prev} - {base_name} * 0.01")
            prev = node
        tails.append(prev)

    level = tails
    lvl = 0
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                name = f"agg_{lvl}_{i // 2}"
                model.define(name, f"{level[i]} + {level[i + 1]}")
                nxt.append(name)
            else:
                nxt.append(level[i])
        level = nxt
        lvl += 1
    model.define("total", level[0], output=True)
    return model, "total", inputs


def node_count(model: FinancialModel) -> int:
    return len(model.module.nodes)


# --------------------------------------------------------------------------- timing
def _time_once(fn) -> tuple[float, Any]:
    t0 = time.perf_counter()
    result = fn()
    return (time.perf_counter() - t0) * 1000.0, result  # milliseconds


@dataclass
class Trial:
    ms: float
    recomputed: int
    reused: int
    value: float


def run_incremental_trial(
    segments: int, depth: int, changed_inputs: dict[str, float], root: str
) -> Trial:
    model, root_name, _ = build_graph(segments, depth)
    model.evaluate()  # untimed warm base
    for name, value in changed_inputs.items():
        model.set(name, value)  # untimed
    ms, result = _time_once(model.evaluate)
    return Trial(
        ms=ms,
        recomputed=len(result.recomputed),
        reused=len(result.reused),
        value=float(result[root_name]),
    )


def run_full_trial(segments: int, depth: int, changed_inputs: dict[str, float], root: str) -> Trial:
    model, root_name, _ = build_graph(segments, depth, overrides=changed_inputs)
    ms, result = _time_once(model.evaluate)  # first-ever evaluate: nothing cached
    return Trial(
        ms=ms,
        recomputed=len(result.recomputed),
        reused=len(result.reused),
        value=float(result[root_name]),
    )


def _median_min_max(vals: list[float]) -> dict[str, float]:
    return {"median": statistics.median(vals), "min": min(vals), "max": max(vals)}


def _build_time_ms(segments: int, depth: int) -> float:
    ms, _ = _time_once(lambda: build_graph(segments, depth))
    return ms


# --------------------------------------------------------- Benchmark A: size sweep
def benchmark_a_incremental_vs_full(rng: random.Random) -> list[dict[str, Any]]:
    """Single changed input, across increasing graph sizes."""
    targets = [100, 1_000, 10_000, 50_000, 100_000]
    reps_by_size = {100: 9, 1_000: 9, 10_000: 9, 50_000: 5, 100_000: 5}
    rows = []
    for target in targets:
        segments = max(2, round((target + 1) / (DEPTH + 2)))
        reps = reps_by_size[target]

        probe_model, root, inputs = build_graph(segments, DEPTH)
        n_nodes = node_count(probe_model)
        changed_input = rng.choice(inputs)
        base_value = 1_000_000.0 + inputs.index(changed_input)
        new_value = base_value * 1.10
        changed = {changed_input: new_value}

        build_ms = _build_time_ms(segments, DEPTH)

        inc_trials = [run_incremental_trial(segments, DEPTH, changed, root) for _ in range(reps)]
        full_trials = [run_full_trial(segments, DEPTH, changed, root) for _ in range(reps)]

        for it, ft in zip(inc_trials, full_trials, strict=True):
            if not math.isclose(it.value, ft.value, rel_tol=1e-9, abs_tol=1e-6):
                raise SystemExit(
                    f"CORRECTNESS FAILURE at graph_nodes={n_nodes}: incremental={it.value} "
                    f"!= full={ft.value} -- aborting rather than reporting an invalid benchmark."
                )

        inc_ms = _median_min_max([t.ms for t in inc_trials])
        full_ms = _median_min_max([t.ms for t in full_trials])
        recomputed_vals = {t.recomputed for t in inc_trials}
        reused_vals = {t.reused for t in inc_trials}
        deterministic_counts = len(recomputed_vals) == 1 and len(reused_vals) == 1

        rows.append(
            {
                "graph_nodes": n_nodes,
                "segments": segments,
                "depth": DEPTH,
                "changed_inputs": 1,
                "changed_inputs_percent": round(100.0 / len(inputs), 6),
                "repetitions": reps,
                "build_ms": round(build_ms, 4),
                "full_ms_median": round(full_ms["median"], 4),
                "full_ms_min": round(full_ms["min"], 4),
                "full_ms_max": round(full_ms["max"], 4),
                "incremental_ms_median": round(inc_ms["median"], 4),
                "incremental_ms_min": round(inc_ms["min"], 4),
                "incremental_ms_max": round(inc_ms["max"], 4),
                "speedup": round(full_ms["median"] / inc_ms["median"], 4)
                if inc_ms["median"] > 0
                else None,
                "recomputed_nodes": inc_trials[0].recomputed,
                "reused_nodes": inc_trials[0].reused,
                "reuse_percent": round(100.0 * inc_trials[0].reused / n_nodes, 4),
                "recompute_count_deterministic_across_reps": deterministic_counts,
                "outputs_matched": True,
            }
        )
        print(
            f"  [A] nodes={n_nodes:>7,}  full={full_ms['median']:>9.3f}ms  "
            f"incr={inc_ms['median']:>8.4f}ms  speedup={rows[-1]['speedup']:>7.2f}x  "
            f"recomputed={inc_trials[0].recomputed:>3}  reused={inc_trials[0].reused:>7,}"
        )
    return rows


# ------------------------------------------------- Benchmark B: change locality
def benchmark_b_change_locality(
    rng: random.Random, *, segments: int, depth: int
) -> list[dict[str, Any]]:
    percentages = [1, 5, 10, 25, 50, 100]
    reps = 7
    probe_model, root, inputs = build_graph(segments, depth)
    n_nodes = node_count(probe_model)
    n_inputs = len(inputs)

    rows = []
    for pct in percentages:
        k = max(1, round(pct / 100.0 * n_inputs))
        chosen = rng.sample(inputs, k)
        changed = {name: (1_000_000.0 + inputs.index(name)) * 1.10 for name in chosen}

        inc_trials = [run_incremental_trial(segments, depth, changed, root) for _ in range(reps)]
        full_trials = [run_full_trial(segments, depth, changed, root) for _ in range(reps)]

        for it, ft in zip(inc_trials, full_trials, strict=True):
            if not math.isclose(it.value, ft.value, rel_tol=1e-9, abs_tol=1e-6):
                raise SystemExit(
                    f"CORRECTNESS FAILURE at pct={pct}: incremental={it.value} != full={ft.value}"
                )

        inc_ms = _median_min_max([t.ms for t in inc_trials])
        full_ms = _median_min_max([t.ms for t in full_trials])
        recomputed_vals = {t.recomputed for t in inc_trials}
        reused_vals = {t.reused for t in inc_trials}

        rows.append(
            {
                "graph_nodes": n_nodes,
                "segments": segments,
                "depth": depth,
                "changed_inputs": k,
                "changed_inputs_percent": pct,
                "repetitions": reps,
                "full_ms_median": round(full_ms["median"], 4),
                "full_ms_min": round(full_ms["min"], 4),
                "full_ms_max": round(full_ms["max"], 4),
                "incremental_ms_median": round(inc_ms["median"], 4),
                "incremental_ms_min": round(inc_ms["min"], 4),
                "incremental_ms_max": round(inc_ms["max"], 4),
                "speedup": round(full_ms["median"] / inc_ms["median"], 4)
                if inc_ms["median"] > 0
                else None,
                "recomputed_nodes": inc_trials[0].recomputed,
                "reused_nodes": inc_trials[0].reused,
                "reuse_percent": round(100.0 * inc_trials[0].reused / n_nodes, 4),
                "recompute_count_deterministic_across_reps": len(recomputed_vals) == 1
                and len(reused_vals) == 1,
                "outputs_matched": True,
            }
        )
        print(
            f"  [B] pct={pct:>3}%  changed={k:>5}/{n_inputs}  full={full_ms['median']:>9.3f}ms  "
            f"incr={inc_ms['median']:>9.4f}ms  speedup={rows[-1]['speedup']:>6.2f}x  "
            f"reuse={rows[-1]['reuse_percent']:>6.2f}%"
        )
    return rows


# -------------------------------------------- Benchmark C: cold/warm/small/large
def benchmark_c_cold_warm(rng: random.Random, *, segments: int, depth: int) -> list[dict[str, Any]]:
    reps = 7
    probe_model, root, inputs = build_graph(segments, depth)
    n_nodes = node_count(probe_model)
    n_inputs = len(inputs)
    rows = []

    # -- cold: first-ever evaluate() on a freshly built, never-evaluated model
    cold_trials = []
    for _ in range(reps):
        model, root_name, _ = build_graph(segments, depth)
        ms, result = _time_once(model.evaluate)
        cold_trials.append(
            Trial(
                ms=ms,
                recomputed=len(result.recomputed),
                reused=len(result.reused),
                value=float(result[root_name]),
            )
        )
    cold_ms = _median_min_max([t.ms for t in cold_trials])
    rows.append(
        {
            "stage": "cold_first_evaluation",
            "graph_nodes": n_nodes,
            "repetitions": reps,
            "ms_median": round(cold_ms["median"], 4),
            "ms_min": round(cold_ms["min"], 4),
            "ms_max": round(cold_ms["max"], 4),
            "recomputed_nodes": cold_trials[0].recomputed,
            "reused_nodes": cold_trials[0].reused,
        }
    )

    # -- warm repeat: same model, evaluate() again with nothing changed
    warm_model, warm_root, _ = build_graph(segments, depth)
    warm_model.evaluate()  # untimed first pass
    warm_trials = []
    for _ in range(reps):
        ms, result = _time_once(warm_model.evaluate)
        warm_trials.append(
            Trial(
                ms=ms,
                recomputed=len(result.recomputed),
                reused=len(result.reused),
                value=float(result[warm_root]),
            )
        )
    warm_ms = _median_min_max([t.ms for t in warm_trials])
    rows.append(
        {
            "stage": "warm_unchanged_repeat",
            "graph_nodes": n_nodes,
            "repetitions": reps,
            "ms_median": round(warm_ms["median"], 4),
            "ms_min": round(warm_ms["min"], 4),
            "ms_max": round(warm_ms["max"], 4),
            "recomputed_nodes": warm_trials[0].recomputed,
            "reused_nodes": warm_trials[0].reused,
        }
    )

    # -- small localized update: 1 input changed
    changed_input = rng.choice(inputs)
    small_change = {changed_input: (1_000_000.0 + inputs.index(changed_input)) * 1.10}
    small_trials = [run_incremental_trial(segments, depth, small_change, root) for _ in range(reps)]
    small_ms = _median_min_max([t.ms for t in small_trials])
    rows.append(
        {
            "stage": "small_localized_update_1_input",
            "graph_nodes": n_nodes,
            "repetitions": reps,
            "ms_median": round(small_ms["median"], 4),
            "ms_min": round(small_ms["min"], 4),
            "ms_max": round(small_ms["max"], 4),
            "recomputed_nodes": small_trials[0].recomputed,
            "reused_nodes": small_trials[0].reused,
        }
    )

    # -- larger update: 50% of inputs changed
    k = max(1, round(0.5 * n_inputs))
    chosen = rng.sample(inputs, k)
    large_change = {name: (1_000_000.0 + inputs.index(name)) * 1.10 for name in chosen}
    large_trials = [run_incremental_trial(segments, depth, large_change, root) for _ in range(reps)]
    large_ms = _median_min_max([t.ms for t in large_trials])
    rows.append(
        {
            "stage": f"larger_update_{k}_of_{n_inputs}_inputs_50pct",
            "graph_nodes": n_nodes,
            "repetitions": reps,
            "ms_median": round(large_ms["median"], 4),
            "ms_min": round(large_ms["min"], 4),
            "ms_max": round(large_ms["max"], 4),
            "recomputed_nodes": large_trials[0].recomputed,
            "reused_nodes": large_trials[0].reused,
        }
    )

    for r in rows:
        print(
            f"  [C] {r['stage']:<38} ms_median={r['ms_median']:>9.4f}  recomputed={r['recomputed_nodes']:>6}  reused={r['reused_nodes']:>7,}"
        )
    return rows


# --------------------------------------------------------- correctness: dirty-set
def verify_dirty_set_matches_dependency_graph(
    segments: int, depth: int, rng: random.Random
) -> dict[str, Any]:
    """Independently confirm that `EvaluationResult.recomputed` for a single-input
    change is exactly `model.dirty_nodes(input) - {input}` -- i.e. the reported
    recompute accounting is not a plausible-looking number but is actually derived
    from (and matches) the real dependency graph's transitive-dependents set.
    """
    model, _root, inputs = build_graph(segments, depth)
    model.evaluate()
    changed = rng.choice(inputs)
    dirty = set(model.dirty_nodes(changed))
    model.set(changed, 1_234_567.0)
    result = model.evaluate()
    recomputed = set(result.recomputed)
    expected = dirty - {changed}  # dirty_nodes includes the input itself; recomputed does not
    matches = recomputed == expected
    return {
        "changed_input": changed,
        "dirty_nodes_count": len(dirty),
        "recomputed_count": len(recomputed),
        "recomputed_equals_dirty_nodes_minus_input": matches,
        "symmetric_difference": sorted(dirty.symmetric_difference(recomputed | {changed}))[:10],
    }


# --------------------------------------------------------------------------- main
def hardware_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "os": platform.platform(),
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "finir_version": finir.__version__,
        "finir_import_path": str(_FINIR_FILE),
        "finir_import_is_site_packages": _IS_SITE_PACKAGES,
    }
    try:
        import subprocess

        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$c=Get-CimInstance Win32_Processor; $m=Get-CimInstance Win32_ComputerSystem; "
                'Write-Output "$($c.Name)|$($c.NumberOfCores)|$($c.NumberOfLogicalProcessors)|$([math]::Round($m.TotalPhysicalMemory/1GB,1))"',
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        parts = out.stdout.strip().split("|")
        if len(parts) == 4:
            info["cpu_model"] = parts[0].strip()
            info["cpu_physical_cores"] = int(parts[1])
            info["cpu_logical_processors"] = int(parts[2])
            info["ram_gb"] = float(parts[3])
    except Exception as exc:  # pragma: no cover - best-effort hardware probe
        info["cpu_probe_error"] = str(exc)
    return info


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"FinIR public benchmark -- finir {finir.__version__} @ {_FINIR_FILE}")
    print(f"is site-packages (public install): {_IS_SITE_PACKAGES}")

    hw = hardware_info()
    print(
        f"CPU: {hw.get('cpu_model', '?')} | cores={hw.get('cpu_physical_cores', '?')} "
        f"logical={hw.get('cpu_logical_processors', '?')} | RAM={hw.get('ram_gb', '?')} GB"
    )
    print(f"OS: {hw['os']} | Python {hw['python_version']} | NumPy {hw['numpy_version']}")

    methodology = {
        "seed": SEED,
        "timed_region": "exactly one model.evaluate() call; construction, warm-up "
        "evaluate, and .set() calls are untimed setup",
        "full_recompute_definition": "a freshly constructed, never-evaluated model "
        "with the changed input value(s) supplied at construction time; its first "
        "evaluate() has nothing cached, so it is an unambiguous full recomputation "
        "using only the public FinancialModel API (no private cache-clear call)",
        "incremental_definition": "a model built once, evaluated once (untimed "
        "warm-up), then the same input change(s) applied via .set() and a second "
        "evaluate() timed -- FinIR's dependency-aware dirty-set propagation "
        "recomputes only the changed cone",
        "statistic": "median of repeated trials (min/max also reported); a fresh "
        "model pair is built for every trial to avoid state leakage between "
        "repetitions",
        "correctness_check": "every trial's incremental and full-recompute output "
        "value (math.isclose, rel_tol=1e-9, abs_tol=1e-6) is compared; any mismatch "
        "aborts the run rather than reporting an invalid result",
        "graph_generator": "this script's own synthetic balanced-tree generator "
        "(benchmarks/public_benchmark.py:build_graph), built only on the public "
        "FinancialModel.input/.define API -- not a modification of FinIR core",
        "graph_generator_deviation_note": "deliberately not FinIR's shipped "
        "finir.benchmark.synthetic.build_segmented_model, whose flat N-ary aggregate "
        "sum recurses once per term in finir.ir.expr.free_refs and hits Python's "
        "default recursion limit above roughly 1,000 segments; this is a real, "
        "reproducible constraint of that helper at that graph shape, not something "
        "patched in core merely to run this benchmark",
        "backend_comparison_scope": "CPU-only (finir.backends.NumpyBackend). No "
        "CUDA GPU is present on this machine (finir.backends.gpu.gpu_available() == "
        "False), so no GPU numbers are reported. finir.backends.ReferenceBackend is "
        "an alias for NumpyBackend, not a distinct implementation, so there is no "
        "second real CPU backend to compare against in finir==0.1.0.",
        "external_framework_comparison_scope": "skipped. Pandas/Polars/DuckDB are "
        "batch dataframe/query engines, not dependency-graph incremental-execution "
        "engines; giving them the 'recompute everything' half of the comparison "
        "would be easy, but the 'incremental' half has no equivalent operation in "
        "those tools for this workload, so any resulting number would compare two "
        "different computational models rather than two implementations of the same "
        "one. Excluded per the instruction to skip apples-to-oranges comparisons "
        "rather than produce a misleading one.",
    }

    rng = random.Random(SEED)
    print("\n=== Benchmark A: incremental vs. full recompute across graph sizes ===")
    a_rows = benchmark_a_incremental_vs_full(rng)

    fixed_size_row = next(
        r for r in a_rows if r["graph_nodes"] > 9_000 and r["graph_nodes"] < 11_000
    )
    b_segments = fixed_size_row["segments"]
    print(
        f"\n=== Benchmark B: change locality at a fixed graph ({fixed_size_row['graph_nodes']:,} nodes) ==="
    )
    b_rows = benchmark_b_change_locality(rng, segments=b_segments, depth=DEPTH)

    print(
        f"\n=== Benchmark C: cold vs. warm vs. small vs. large update (same {fixed_size_row['graph_nodes']:,}-node graph) ==="
    )
    c_rows = benchmark_c_cold_warm(rng, segments=b_segments, depth=DEPTH)

    print("\n=== Correctness: recomputed-node set vs. actual dependency graph ===")
    dirty_check = verify_dirty_set_matches_dependency_graph(b_segments, DEPTH, rng)
    print(
        f"  changed_input={dirty_check['changed_input']!r}  "
        f"recomputed_equals_dirty_nodes_minus_input={dirty_check['recomputed_equals_dirty_nodes_minus_input']}"
    )
    if not dirty_check["recomputed_equals_dirty_nodes_minus_input"]:
        raise SystemExit(
            "CORRECTNESS FAILURE: recomputed node set does not match the dependency graph."
        )

    payload = {
        "benchmark_suite": "finir_public_benchmark",
        "date_utc": RUN_DATE,
        "finir_version": finir.__version__,
        "synthetic_workload": True,
        "hardware": hw,
        "methodology": methodology,
        "correctness": {
            "all_incremental_vs_full_outputs_matched": True,
            "dirty_set_verification": dirty_check,
        },
        "results": {
            "incremental_vs_full": a_rows,
            "change_locality": b_rows,
            "cold_warm_update": c_rows,
        },
    }

    json_path = RESULTS_DIR / f"finir_public_benchmark_{RUN_DATE}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    csv_path = RESULTS_DIR / f"finir_public_benchmark_{RUN_DATE}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "benchmark",
                "graph_nodes",
                "changed_inputs",
                "changed_inputs_percent",
                "repetitions",
                "full_ms_median",
                "incremental_ms_median",
                "speedup",
                "recomputed_nodes",
                "reused_nodes",
                "reuse_percent",
            ]
        )
        for r in a_rows:
            writer.writerow(
                [
                    "incremental_vs_full",
                    r["graph_nodes"],
                    r["changed_inputs"],
                    r["changed_inputs_percent"],
                    r["repetitions"],
                    r["full_ms_median"],
                    r["incremental_ms_median"],
                    r["speedup"],
                    r["recomputed_nodes"],
                    r["reused_nodes"],
                    r["reuse_percent"],
                ]
            )
        for r in b_rows:
            writer.writerow(
                [
                    "change_locality",
                    r["graph_nodes"],
                    r["changed_inputs"],
                    r["changed_inputs_percent"],
                    r["repetitions"],
                    r["full_ms_median"],
                    r["incremental_ms_median"],
                    r["speedup"],
                    r["recomputed_nodes"],
                    r["reused_nodes"],
                    r["reuse_percent"],
                ]
            )

    print(f"\nWrote {json_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
