# FinIR

**A financial intermediate representation and incremental execution runtime for AI systems.**

AI systems increasingly reason about finance, but their numerical execution still
falls back to generated Python, spreadsheets, SQL, or generic tensor frameworks.
FinIR gives financial reasoning a dedicated compiler target.

```
AI Financial Intent
        ↓
      FinIR
        ↓
Dependency Analysis
        ↓
Incremental Execution
        ↓
CPU / SIMD / GPU
        ↓
Financial Result
```

[![CI](https://github.com/Lethabo-Scofield/finir/actions/workflows/ci.yml/badge.svg)](https://github.com/Lethabo-Scofield/finir/actions/workflows/ci.yml)
&nbsp;License: Apache-2.0 &nbsp;·&nbsp; Python 3.11+ &nbsp;·&nbsp; CPU-first, optional GPU

## Quick start

```python
from finir import FinancialModel

model = FinancialModel()

model.input("revenue", 500_000_000, currency="ZAR")
model.input("cogs", 300_000_000, currency="ZAR")
model.input("opex", 120_000_000, currency="ZAR")

model.define("gross_profit", "revenue - cogs")
model.define("ebitda", "gross_profit - opex")

model.evaluate()

scenario = model.what_if(cogs="+4%")

print(scenario["ebitda"])
```

Change one assumption and FinIR recomputes **only the affected part of the graph**:

```
Input changed:
  COGS

Recomputed:
  COGS → Gross Profit → EBITDA → Gross Margin → Cash Flow

Reused (from cache):
  Revenue, Payroll, Debt, Receivables, ...
```

Install:

```bash
pip install -e ".[dev]"     # from source (not yet on PyPI)
finir --help
```

## Why FinIR

When an AI needs to compute *"increase supplier costs 7% and extend payment terms
30→60 days,"* it usually translates that into arbitrary generated code — inefficient,
non-deterministic, unaudited, and recomputed from scratch every turn. FinIR replaces
that with a standard boundary:

```
financial intent  →  FinIR  →  deterministic, incremental financial execution
```

It understands financial semantics (revenue, COGS, gross margin, EBITDA, working
capital, receivables/payables, free cash flow, NPV, unit economics, payment terms,
…) and their computational dependencies — so it can recompute only what changed and
reuse the rest.

## What is a Financial IR?

A typed computation graph with a finance-native type system:

```
revenue      = input money[ZAR]
cogs         = input money[ZAR]
gross_profit = revenue - cogs        : money[ZAR]
gross_margin = gross_profit / revenue : ratio
```

`money - money → money` (same currency, else an error); `money / money → ratio`;
`money + days` is a type error. See [docs/ir.md](docs/ir.md) and
[docs/type-system.md](docs/type-system.md).

## Architecture

```
Agent / Developer API → FinIR Builder → Financial IR → Compiler Passes
  → Execution Plan → Incremental Runtime → Kernel Backend → CPU / SIMD / GPU
```

Each layer is cleanly separated. See [docs/architecture.md](docs/architecture.md).

## Incremental execution

Changing one input invalidates only its downstream cone; the next evaluation
recomputes exactly those nodes and reuses everything else in O(1). This is FinIR's
reason to exist — see [docs/runtime.md](docs/runtime.md) and
[docs/caching.md](docs/caching.md).

## Scenario engine

`what_if`, named `scenarios`, and vectorized `run_scenarios` over million-row
batches. See [docs/scenarios.md](docs/scenarios.md).

## Financial types

`money[CCY]`, `percentage`, `ratio`, `days`, `quantity`, `rate`, `series`,
`scenario`, `scalar`, `bool` — enforced at compile time. See
[docs/type-system.md](docs/type-system.md).

## Kernels

Arithmetic, corporate finance, working capital, time-value-of-money, and basic risk
— plus a `@finir.kernel` extension point. Deliberately small (not a quant library).
See [docs/kernels.md](docs/kernels.md).

## Compiler passes

Validation, type checking, constant folding, CSE, dead-node elimination, dependency
pruning, scenario vectorization, fusion analysis, cache planning. Inspect with
`finir compile model.finir --show-passes`. See [docs/compiler.md](docs/compiler.md).

## Agent integration

Core FinIR consumes **structured** intent (`apply_intent`); natural-language
interpretation is an optional `IntentCompiler` layer (a dependency-free
`MockIntentCompiler` ships for offline use). The model interprets; the runtime
computes. See [docs/agent-integration.md](docs/agent-integration.md).

## CPU / GPU dispatch

CPU-first and fully usable with no optional dependencies. A workload-aware planner
sends very large scenario batches to an optional CuPy GPU backend when present. See
[docs/backends.md](docs/backends.md).

## Benchmarks

```bash
finir benchmark --full
python benchmarks/run_benchmarks.py     # writes benchmarks/results/
```

On the reference machine: **1.7×–2.2× faster** iterative reasoning vs. full
recompute (up to 99.6% cache hits), and ~1,000,000 scenarios in ~46 ms on CPU. All
numbers are measured, never hard-coded. See [docs/performance.md](docs/performance.md).

## Research

- [research/experiment_001_incremental_financial_reasoning.md](research/experiment_001_incremental_financial_reasoning.md) — incremental vs. full recompute
- [research/experiment_002_backend_dispatch.md](research/experiment_002_backend_dispatch.md) — CPU/GPU crossover (GPU unverified locally)
- [research/prior_art.md](research/prior_art.md) — critical positioning vs. spreadsheets, incremental-computation systems, JAX/XLA/MLIR, QuantLib, planning engines, and more

We do **not** claim FinIR is a first or a breakthrough. The working hypothesis —
that there is no widely-adopted open finance-specific IR designed as the execution
boundary between AI financial intent and incremental computation — remains a
hypothesis pending a formal prior-art review.

## Extending FinIR

Custom kernels, backends, and templates; a stable JSON IR for other-language
bindings. See [docs/extending.md](docs/extending.md).

## Roadmap

- Larger real-model benchmarks and agent-trace evaluation.
- Measured GPU dispatch thresholds on CUDA hardware.
- Optional lowering onto a tensor compiler (XLA/MLIR) for very large graphs.
- Language bindings (TypeScript/Rust) over the JSON IR.
- Autodiff / sensitivities as an optional layer.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Quality gates: `ruff check .`,
`ruff format --check .`, `mypy src`, `pytest`. CPU-only; no network for core tests.

## Citation

See [CITATION.cff](CITATION.cff).

## Acknowledgements

Early research exploration was inspired by omni-modal scientific-reasoning systems
(including work such as OmniScientist). FinIR is **independent**: no OmniScientist
code and no runtime dependency on it.

## License

Apache-2.0 — see [LICENSE](LICENSE).
