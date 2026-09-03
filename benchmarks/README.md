# Benchmarks

Real, executed benchmarks — no hard-coded numbers.

```bash
python benchmarks/run_benchmarks.py      # writes benchmarks/results/benchmark_results.json
finir benchmark --full                   # incremental-vs-recompute table
python benchmarks/public_benchmark.py    # public-research-page benchmark (see below)
```

## `public_benchmark.py` — the public research-page benchmark

Benchmarks the **public PyPI `finir==0.1.0`** package specifically (it refuses to run
against a local/editable install — see the script's own provenance check) across
graph sizes 98–100,002 nodes, change-locality (1–100% of inputs changed at once), and
cold/warm/small/large-update timing. Full methodology, hardware, and every measured
point are embedded in `results/finir_public_benchmark_<date>.json` (and a flattened
`.csv`). Uses a purpose-built synthetic graph generator (balanced pairwise-sum tree,
not FinIR's shipped `finir.benchmark.synthetic.build_segmented_model` — see the
script's docstring for why: the shipped generator's flat aggregate-sum expression
hits Python's recursion limit above ~1,000 segments). No FinIR core code is modified.

## What is measured

- **Incremental vs. full recompute** (`finir.benchmark.incremental`): an iterative
  agent workload over synthetic models of 41–2,101 nodes. The two conditions run the
  same graph/kernels; only the cache differs. Reports wall-clock, cache-hit ratio,
  and speedup.
- **Scenario batch** (`finir.benchmark.scenario_bench`): vectorized-CPU (and GPU if a
  device is present) timing across batch sizes 1e3–1e6. GPU rows appear only on real
  hardware.

## Results

`results/benchmark_results.json` includes hardware metadata (platform, Python,
NumPy, FinIR versions) alongside the timings. It is committed as a **reference**
snapshot from the author's machine; your numbers will differ. Re-run to regenerate.

See [../docs/performance.md](../docs/performance.md) for interpretation and honest
caveats (including the fusion negative result and the earlier slow cache design).
