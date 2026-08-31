# Benchmarks

Real, executed benchmarks — no hard-coded numbers.

```bash
python benchmarks/run_benchmarks.py      # writes benchmarks/results/benchmark_results.json
finir benchmark --full                   # incremental-vs-recompute table
```

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
