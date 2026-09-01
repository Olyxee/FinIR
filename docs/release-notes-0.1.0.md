# FinIR 0.1.0: a compiler target for AI financial computation

First public release of **FinIR** — a financial intermediate representation and
incremental execution runtime for AI systems.

```bash
pip install finir
```

## What's in it

- **Finance-typed IR.** A typed computation graph with a `.finir` text form and a
  lossless JSON interchange format. The type system enforces the algebra of finance
  at compile time (`money - money → money` same-currency; `money / money → ratio`;
  `money + days` and `USD + ZAR` are errors).
- **Incremental dirty-set runtime.** Changing one input invalidates only its
  downstream cone; the next evaluation recomputes exactly those nodes and reuses the
  rest in O(1). On the reference machine this is **1.7×–2.2× faster** than full
  recompute with up to 99.6% cache reuse (measured; see docs/performance.md).
- **Dependency-aware reuse & a finance-native cache** with hit/reuse metrics.
- **Scenario execution.** `what_if`, named `scenarios`, and vectorized
  `run_scenarios` over million-row batches (~1,000,000 scenarios in ~46 ms on CPU).
- **Structured intent contract (schema v1.0).** A canonical, versioned JSON envelope
  that a natural-language layer emits and the runtime validates and executes
  (`apply_intent`), with `valid`/`ambiguous`/`unsupported`/`invalid` statuses so
  vague language never becomes invented numbers.
- **CPU backend** (NumPy) — the default, needs nothing else.
- **Optional GPU backend** (CuPy) behind `pip install "finir[gpu]"`, with a
  workload-aware dispatch planner.
- **CLI** (`finir run/compile/inspect/graph/benchmark/doctor`).
- **Kernel library** (arithmetic, corporate finance, working capital, time value of
  money, basic risk) plus a `@finir.kernel` extension point.
- **Benchmark suite** and two **research experiments** (incremental reasoning;
  backend dispatch) — all numbers measured, never hard-coded — plus a critical
  prior-art analysis.
- **Apache-2.0**, Python 3.11–3.13, CPU-first.

## Honest caveats

- **GPU performance has not yet been verified on CUDA hardware.** The GPU backend is
  optional and unit-tested via guards; its dispatch threshold is a heuristic pending
  measurement (see research/experiment_002_backend_dispatch.md).
- FinIR is deliberately **not** a quant library; the kernel set is small.
- Positioning vs. spreadsheets, incremental-computation systems, JAX/XLA/MLIR,
  QuantLib, and planning engines is examined in research/prior_art.md. We make **no**
  claim of being a first or a breakthrough — the novelty is a compositional
  hypothesis pending a formal prior-art review.

## Links

- Docs: https://github.com/Olyxee/finir/tree/main/docs
- Intent contract: https://github.com/Olyxee/finir/blob/main/docs/intent-contract.md
- Changelog: https://github.com/Olyxee/finir/blob/main/CHANGELOG.md
