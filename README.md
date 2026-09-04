# FinIR

**A financial intermediate representation and incremental execution runtime for AI systems.**

In one sentence: FinIR is a small, typed "compiler" for financial calculations —
instead of an AI regenerating and re-running an entire spreadsheet-like model every
time one number changes, it describes the model to FinIR once, and FinIR recomputes
only what actually depends on the thing that changed.

AI systems increasingly reason about finance, but their numerical execution still
falls back to generated Python, spreadsheets, SQL, or generic tensor frameworks —
slow to re-run, hard to audit, and with no shared notion of what "revenue" or "days"
even mean as types. FinIR gives financial reasoning a dedicated compiler target
instead.

![FinIR: financial intent flowing through dependency analysis and incremental execution to CPU/SIMD/GPU](https://github.com/user-attachments/assets/20298bac-2d01-4b65-8b83-01643e500851)

[![CI](https://github.com/Olyxee/finir/actions/workflows/ci.yml/badge.svg)](https://github.com/Olyxee/finir/actions/workflows/ci.yml)
&nbsp;License: Apache-2.0 &nbsp;·&nbsp; Python 3.11+ &nbsp;·&nbsp; CPU-first, optional GPU

```
Financial Intent
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

## Install

```bash
pip install finir
```

```bash
python -c "import finir; print(finir.__version__)"
finir --help
finir doctor
```

CPU-first: `pip install finir` needs no GPU. Optional extras: `pip install "finir[gpu]"`
(CuPy GPU backend), `pip install "finir[viz]"` (Graphviz SVG rendering). Develop from
source with `git clone https://github.com/Olyxee/finir && cd finir && pip install -e ".[dev]"`.

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

Change one assumption and FinIR recomputes **only the affected part of the graph** —
it never starts over:

```
Input changed:
  COGS

Recomputed:
  COGS → Gross Profit → EBITDA → Gross Margin → Cash Flow

Reused (from cache):
  Revenue, Payroll, Debt, Receivables, ...
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

An **intermediate representation (IR)** is just a structured, typed description of a
computation that a compiler can analyze before running it — the same idea C compilers
and TensorFlow graphs use, applied here to financial models instead of general code
or tensors. FinIR's IR is a typed computation graph with a finance-native type system:

```
revenue      = input money[ZAR]
cogs         = input money[ZAR]
gross_profit = revenue - cogs        : money[ZAR]
gross_margin = gross_profit / revenue : ratio
```

Because the types carry financial meaning, not just numeric shape, FinIR can catch
mistakes at compile time: `money - money → money` (same currency, else an error);
`money / money → ratio`; `money + days` is a type error. See
[docs/ir.md](https://github.com/Olyxee/finir/blob/main/docs/ir.md) and
[docs/type-system.md](https://github.com/Olyxee/finir/blob/main/docs/type-system.md).

## Architecture

Each stage below is a clean, separately-testable layer — an agent or developer never
has to touch anything past the first arrow:

```
Agent / Developer API → FinIR Builder → Financial IR → Compiler Passes
  → Execution Plan → Incremental Runtime → Kernel Backend → CPU / SIMD / GPU
```

See [docs/architecture.md](https://github.com/Olyxee/finir/blob/main/docs/architecture.md).

## Incremental execution

This is FinIR's core reason to exist. Changing one input invalidates only its
downstream cone in the dependency graph; the next evaluation recomputes exactly
those nodes and reuses everything else in O(1) — a dict lookup, not a re-derived
cache key. See [docs/runtime.md](https://github.com/Olyxee/finir/blob/main/docs/runtime.md) and
[docs/caching.md](https://github.com/Olyxee/finir/blob/main/docs/caching.md).

## Scenario engine

`what_if`, named `scenarios`, and vectorized `run_scenarios` over million-row
batches. See [docs/scenarios.md](https://github.com/Olyxee/finir/blob/main/docs/scenarios.md).

## Financial types

`money[CCY]`, `percentage`, `ratio`, `days`, `quantity`, `rate`, `series`,
`scenario`, `scalar`, `bool` — enforced at compile time. See
[docs/type-system.md](https://github.com/Olyxee/finir/blob/main/docs/type-system.md).

## Kernels

Arithmetic, corporate finance, working capital, time-value-of-money, and basic risk
— plus a `@finir.kernel` extension point. Deliberately small (not a quant library).
See [docs/kernels.md](https://github.com/Olyxee/finir/blob/main/docs/kernels.md).

## Compiler passes

Validation, type checking, constant folding, CSE, dead-node elimination, dependency
pruning, scenario vectorization, fusion analysis, cache planning. Inspect with
`finir compile model.finir --show-passes`. See [docs/compiler.md](https://github.com/Olyxee/finir/blob/main/docs/compiler.md).

## Agent integration

Core FinIR consumes **structured** intent (`apply_intent`); natural-language
interpretation is an optional `IntentCompiler` layer (a dependency-free
`MockIntentCompiler` ships for offline use) — the model *interprets*, the runtime
*computes*, and that boundary is never blurred. See
[docs/agent-integration.md](https://github.com/Olyxee/finir/blob/main/docs/agent-integration.md)
and, for the canonical NL → FinIR contract, [docs/intent-contract.md](https://github.com/Olyxee/finir/blob/main/docs/intent-contract.md).

## CPU / GPU dispatch

CPU-first and fully usable with no optional dependencies. A workload-aware planner
sends very large scenario batches to an optional CuPy GPU backend when present. See
[docs/backends.md](https://github.com/Olyxee/finir/blob/main/docs/backends.md).

## Benchmarks

```bash
finir benchmark --full
python benchmarks/run_benchmarks.py         # iterative-reasoning workload -> benchmarks/results/
python benchmarks/public_benchmark.py       # incremental vs. full recompute across graph sizes
```

On the reference machine, the iterative-reasoning benchmark shows **1.7×–2.2× faster**
turn-by-turn agent reasoning vs. full recompute (up to 99.6% cache hits), and
~1,000,000 scenarios in ~46 ms on CPU. A separate, independently-reproducible
benchmark (`benchmarks/public_benchmark.py`, run against the published `finir==0.1.0`
package) measures a different question — how the advantage scales with graph size —
and finds **15×–24× speedup** holding across graphs from ~100 to ~100,000 nodes for a
single changed input, with cache reuse up to ~86%. All numbers are measured, never
hard-coded; see [docs/performance.md](https://github.com/Olyxee/finir/blob/main/docs/performance.md)
and `benchmarks/results/` for full methodology and raw data.

## Research

- [research/experiment_001_incremental_financial_reasoning.md](https://github.com/Olyxee/finir/blob/main/research/experiment_001_incremental_financial_reasoning.md) — incremental vs. full recompute
- [research/experiment_002_backend_dispatch.md](https://github.com/Olyxee/finir/blob/main/research/experiment_002_backend_dispatch.md) — CPU/GPU crossover (GPU unverified locally)
- [research/prior_art.md](https://github.com/Olyxee/finir/blob/main/research/prior_art.md) — critical positioning vs. spreadsheets, incremental-computation systems, JAX/XLA/MLIR, QuantLib, planning engines, and more

We do **not** claim FinIR is a first or a breakthrough. The working hypothesis —
that there is no widely-adopted open finance-specific IR designed as the execution
boundary between AI financial intent and incremental computation — remains a
hypothesis pending a formal prior-art review.

## Extending FinIR

Custom kernels, backends, and templates; a stable JSON IR for other-language
bindings. See [docs/extending.md](https://github.com/Olyxee/finir/blob/main/docs/extending.md).

## Roadmap

- Larger real-model benchmarks and agent-trace evaluation.
- Measured GPU dispatch thresholds on CUDA hardware.
- Optional lowering onto a tensor compiler (XLA/MLIR) for very large graphs.
- Language bindings (TypeScript/Rust) over the JSON IR.
- Autodiff / sensitivities as an optional layer.

## Contributing

See [CONTRIBUTING.md](https://github.com/Olyxee/finir/blob/main/CONTRIBUTING.md). Quality gates: `ruff check .`,
`ruff format --check .`, `mypy src`, `pytest`. CPU-only; no network for core tests.

## Citation

See [CITATION.cff](https://github.com/Olyxee/finir/blob/main/CITATION.cff).

## Acknowledgements

Early research exploration was inspired by omni-modal scientific-reasoning systems
(including work such as OmniScientist). FinIR is **independent**: no OmniScientist
code and no runtime dependency on it.

## License

Apache-2.0 — see [LICENSE](https://github.com/Olyxee/finir/blob/main/LICENSE).
