# Changelog

All notable changes to FinIR are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-09-05

Documentation-only patch release. **No changes to `finir`'s code, public API, or
runtime behavior** — every file under `src/finir/` is byte-identical to `0.1.0`.
Released solely to refresh the README that PyPI displays (PyPI renders the README
bundled with a given version at upload time; it does not update when the GitHub
repository changes, so the 0.1.0 page was showing a stale README).

### Changed

- README: replaced the hero image's raw `<img width height>` HTML tag with plain
  Markdown image syntax, so it scales to fit PyPI's narrower content column instead
  of rendering oversized.
- README: added a plain-language explanation of what FinIR does up front, a lead-in
  to the "What is a Financial IR?" section, a link to `docs/intent-contract.md`, a
  reference to `benchmarks/public_benchmark.py`, and removed em dashes throughout.
- CI/dev tooling: excluded the generated `release/huggingface/` Hugging Face
  publish-staging export from the root `ruff` lint scope (it was being linted under
  the wrong config and failing CI on a false positive; not shipped in the package).
- Added `benchmarks/public_benchmark.py`: an independently-reproducible benchmark of
  incremental execution vs. full recomputation across graph sizes, run against the
  published `finir==0.1.0` package. Not part of the installed package; see
  `benchmarks/results/` for methodology and raw data.

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

[0.1.0]: https://github.com/Olyxee/finir/releases/tag/v0.1.0
