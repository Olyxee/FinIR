# Experiment 002 — Backend dispatch thresholds

> Reproduce: `python research/reproduce_experiment_002.py` (writes
> `research/results_002.json`). GPU rows are produced only on real CUDA hardware and
> are **never** fabricated.

## Research question

At what scenario-batch size does GPU execution become beneficial relative to
vectorized CPU execution for finance-native computation graphs? The empirical
crossover should set the dispatch planner's `GPU_MIN_ELEMENTS` threshold.

## Method

Time a fixed arithmetic scenario graph while broadcasting one input across batches
of increasing size (1e3 → 5e6). Measure vectorized-CPU (NumPy) always, and GPU
(CuPy) only when a device is present. The crossover is the smallest size where GPU
beats CPU.

## Results (this machine — CPU only)

Hardware: Windows-11, Python 3.13.7, NumPy 2.5.2. **No CUDA device**, so GPU is not
measured here.

| batch size | CPU time | GPU time |
|------------|----------|----------|
| 1,000      | 0.00008 s | n/a |
| 10,000     | 0.00029 s | n/a |
| 100,000    | 0.00271 s | n/a |
| 1,000,000  | 0.04557 s | n/a |
| 5,000,000  | 0.26532 s | n/a |

CPU scenario throughput is high and scales roughly linearly with batch size
(~19M scenarios/s at 1M on this machine for this graph). **The GPU crossover is
UNVERIFIED locally.**

## What we can and cannot conclude

- **Can:** vectorized CPU already handles up to millions of finance scenarios in
  tens of milliseconds for arithmetic graphs, so for the first release CPU is a
  strong default and the "CPU-only usability" requirement is met with margin.
- **Cannot:** we cannot state a real GPU crossover without a GPU. The current
  dispatch default (`GPU_MIN_ELEMENTS = 250_000`) is a **heuristic placeholder**,
  not a measured threshold.

## Expected shape (hypothesis, to test on GPU)

On typical CUDA hardware we expect:
- below ~10⁴–10⁵ elements, host↔device transfer + launch overhead makes GPU slower;
- above some crossover (commonly 10⁵–10⁶ elements for simple elementwise graphs),
  GPU throughput wins and the gap grows with size;
- named kernels (NPV, risk) that FinIR currently runs on the host would need device
  implementations to benefit — today they force a host round-trip.

## Action

Until measured on GPU hardware, keep the planner's threshold conservative and
documented as a heuristic. When a CUDA machine is available, re-run this experiment,
record the crossover in `results_002.json`, and set `GPU_MIN_ELEMENTS` from data.

## Limitations

- CPU-only run: the central number (the crossover) is not produced here.
- Single graph shape and one machine; thresholds are hardware- and graph-dependent.
- GPU path currently accelerates arithmetic-graph batches only, not named kernels.
