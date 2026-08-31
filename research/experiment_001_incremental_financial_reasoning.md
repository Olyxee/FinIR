# Experiment 001 — Incremental financial reasoning

> Reproduce: `python research/reproduce_experiment_001.py` (writes
> `research/results_001.json`). All numbers below come from real timed runs; none
> are hard-coded.

## Research question

Can a finance-native intermediate representation with dependency-aware caching
materially reduce the computational cost of **iterative** financial reasoning
performed by an AI system, compared with full recomputation of the model each turn?

## Hypothesis

For repeated small changes (the pattern an agent produces when exploring
scenarios), FinIR incremental execution costs strictly less — in wall-clock time
and in nodes recomputed — than recomputing the whole model each turn, and the gap
widens with model size.

## Method

Two conditions run the **same** graph and the **same** kernels:

- **baseline** — the cache is cleared each turn, forcing a full recompute of every
  needed node. This is arithmetically identical to regenerating and re-executing
  the whole model (what an agent does when it emits fresh NumPy each turn).
- **finir** — the cache stays warm; dirty-set propagation recomputes only the
  changed input's downstream cone and reuses everything else in O(1).

Two workloads:

1. **Agent turn sequence** on a small company model (6 computed nodes): a base
   evaluation followed by an item-22-style sequence of single-input changes
   (revenue +5%, +8%, cogs +3%, payment terms 30→60d, opex −4%), repeated to 1,000
   turns.
2. **Scaling**: synthetic segmented models from 41 to 2,101 nodes, 40–100 turns.

### Hardware / software (this run)

- Platform: Windows-11 (10.0.26200), Python 3.13.7, NumPy 2.5.2, FinIR 0.1.0.
- Single process, `time.perf_counter`, best-of-repeats where noted.

## Results

### Agent workload (1,000 turns, 6-node model)

| condition | time | node-recomputes | cache hit |
|-----------|------|-----------------|-----------|
| baseline (full recompute) | 0.0355 s | 6,000 | — |
| **finir (incremental)** | **0.0223 s** | **3,600** | 40.0% |

- **Speedup: 1.59×**, **recompute reduction: 40.0%**.
- The small model interconnects tightly (most nodes flow through `gross_profit`),
  so the reuse ceiling is modest here — which is exactly what the scaling test
  probes next.

### Scaling (nodes → speedup)

| nodes | speedup | cache hit |
|-------|---------|-----------|
| 41    | 1.89×   | 87.1% |
| 241   | 1.98×   | 97.0% |
| 841   | 2.21×   | 99.0% |
| 2,101 | 2.19×   | 99.6% |

As the model grows and each change touches a smaller fraction of it, cache-hit rate
approaches 100% and the wall-clock speedup rises toward ~2.2× and holds.

## Interpretation

- The hypothesis holds on this suite: incremental execution recomputed 40% fewer
  nodes on the agent workload and ran 1.6–2.2× faster across sizes, with cache-hit
  ratios of 87–99.6%.
- The wall-clock speedup is **bounded by fan-in**: the segmented model's top-level
  aggregate depends on every segment, so it recomputes every turn (a 300-way sum),
  capping the ratio near ~2.2×. A model without a global aggregate, or with
  expensive per-node kernels, would show a larger gap; a fully-connected model
  would show none. FinIR helps in proportion to how *local* changes are.

## Limitations

1. **Cheap arithmetic.** Each node here is a single float op, so Python-level
   traversal overhead is a large share of the cost; the incremental win is real but
   modest. With costlier kernels (NPV over long series, large vectorized batches),
   the same reuse avoids much more work.
2. **Synthetic graphs.** Real financial models vary in shape; the speedup depends
   on locality of change, which this experiment controls but real workloads do not.
3. **CPU, single process.** No parallelism is exploited here.
4. **The baseline is the same engine minus caching**, not a separately-optimized
   NumPy program; it isolates the value of incrementality, not of FinIR vs. all
   possible hand-written code.

## Conclusion

On this suite, a finance-native IR with dependency-aware caching reduces the compute
of iterative financial reasoning: **1.6–2.2× faster, up to 99.6% cache hits, 40%
fewer recomputes** on the agent workload. This demonstrates the mechanism and the
measurement methodology; efficacy on real agent traces and larger models remains to
be shown.
