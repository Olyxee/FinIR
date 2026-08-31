# Performance

All numbers here come from `benchmarks/run_benchmarks.py` and the research scripts —
run them yourself; nothing is hard-coded. Results below are from the project's
reference machine (Windows-11, Python 3.13, NumPy 2.5.2, **CPU only**).

## Incremental vs. full recompute (iterative agent workload)

| model nodes | turns | baseline | finir | speedup | cache hit |
|-------------|-------|----------|-------|---------|-----------|
| 41    | 40  | 0.0019 s | 0.0011 s | 1.69× | 87.1% |
| 241   | 60  | 0.0161 s | 0.0084 s | 1.91× | 97.0% |
| 841   | 80  | 0.0785 s | 0.0364 s | 2.16× | 99.0% |
| 2,101 | 100 | 0.2621 s | 0.1190 s | 2.20× | 99.6% |

The speedup rises with model size and holds around ~2.2×. It is **bounded by
fan-in**: a global aggregate that depends on every node recomputes every turn,
capping the ratio. FinIR helps in proportion to how *local* a change is.

## Scenario batches (vectorized CPU)

| batch size | CPU time |
|------------|----------|
| 1,000      | 0.00008 s |
| 100,000    | 0.00271 s |
| 1,000,000  | 0.04557 s |
| 5,000,000  | 0.26532 s |

Millions of arithmetic scenarios in tens to hundreds of milliseconds on CPU.

## GPU

**Unverified locally** — the reference machine has no CUDA device, so no GPU numbers
are reported (we do not fabricate them). The GPU backend is unit-testable via
`gpu_available()` guards; its dispatch threshold is a heuristic pending measurement
on real hardware (see
[../research/experiment_002_backend_dispatch.md](../research/experiment_002_backend_dispatch.md)).

## Kernel fusion (honest negative result)

We prototyped fusing adjacent arithmetic nodes into single kernels. NumPy already
fuses elementwise operations internally, so a separate FinIR fusion kernel produced
**no material CPU speedup**. The fusion pass therefore *identifies* fusable chains
but does not emit fused kernels — we chose not to ship complexity that does not pay
for itself, and we say so rather than claim a win.

## Design note: why the first cache design was slow

An earlier engine keyed each node by a signature tuple over its transitive input
versions. Correct, but rebuilding those tuples every evaluation cost *more* than the
trivial arithmetic — making "incremental" slower than recompute on large cheap
graphs (measured 0.73× at 2,101 nodes). The current validity-set / dirty-propagation
engine fixed it (2.2× at the same size). Reuse is now an O(1) lookup.

## Caveats

- Cheap per-node arithmetic makes Python traversal overhead a large share of cost;
  the win grows with per-node cost and model size.
- Synthetic graphs; real financial models vary in shape.
- Single process, CPU. No parallelism exploited in the engine itself.
