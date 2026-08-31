# Changelog

All notable changes to FinIR are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-31

First release of **FinIR** — a financial intermediate representation and incremental
execution runtime for AI systems.

> This repository previously hosted a different project (an economic-event
> framework). That direction has been **retired**; FinIR is a new project with a new
> purpose. No results from the previous project are carried over or presented as
> FinIR results.

### Added

- **Financial IR** (`finir.ir`): typed computation modules with an expression AST, a
  `.finir` textual format, a parser, a lossless JSON interchange format, and a
  validator.
- **Finance-aware type system** (`finir.types`): `money[CCY]`, `percentage`, `ratio`,
  `days`, `quantity`, `rate`, `series`, `scenario`, `scalar`, `bool`, with a compile-
  time algebra (e.g. `money/money → ratio`; `money + days` and `USD + ZAR` are errors).
- **Compiler passes** (`finir.compiler`): validation, type checking, constant
  folding, common-subexpression elimination, dead-node elimination, dependency
  pruning, scenario-vectorization analysis, fusion analysis, cache planning.
- **Incremental runtime** (`finir.runtime`): dependency-aware engine that recomputes
  only a changed input's downstream cone and reuses the rest in O(1); computation
  cache with hit/reuse metrics; versioned `ModelState` snapshots.
- **Scenario engine**: `what_if`, named `scenarios`, and vectorized `run_scenarios`
  over million-row batches.
- **Backends** (`finir.backends`): reference/vectorized CPU (NumPy) and an optional
  GPU backend (CuPy), with a workload-aware dispatch planner.
- **Kernel library** (`finir.kernels`): arithmetic, corporate finance, working
  capital, time-value-of-money, and basic risk — plus a `@finir.kernel` extension
  point.
- **Standard library** (`finir.stdlib`): income-statement, working-capital,
  operating-model, DCF, risk, and SaaS unit-economics templates.
- **Agent integration**: structured-intent `apply_intent` and an optional
  `IntentCompiler` interface with a dependency-free `MockIntentCompiler`.
- **CLI** (`finir`): `run`, `compile`, `inspect`, `graph`, `benchmark`, `doctor`,
  `version`.
- **Graph export**: Graphviz DOT and JSON.
- **Safe numerics**: configurable division-by-zero / non-finite handling; Decimal
  path for money-sensitive scalar math.
- **Benchmarks** (`benchmarks/`, `finir.benchmark`): incremental-vs-recompute and
  scenario-batch suites that write real results with hardware metadata.
- **Research**: Experiment 001 (incremental financial reasoning), Experiment 002
  (backend dispatch), and a critical prior-art analysis.
- **Docs** (`docs/`): architecture, IR, type system, compiler, runtime, caching,
  scenarios, kernels, financial semantics, backends, agent integration, performance,
  extending.

[0.1.0]: https://github.com/Lethabo-Scofield/finir/releases/tag/v0.1.0
