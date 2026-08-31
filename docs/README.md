# FinIR documentation

Start here.

## Concepts
- [architecture.md](architecture.md) — the layered design
- [ir.md](ir.md) — the intermediate representation (`.finir`, JSON, parser)
- [type-system.md](type-system.md) — finance-aware types
- [financial-semantics.md](financial-semantics.md) — metrics and their dependencies

## Execution
- [compiler.md](compiler.md) — the pass pipeline
- [runtime.md](runtime.md) — incremental execution
- [caching.md](caching.md) — the computation cache
- [scenarios.md](scenarios.md) — what-if and scenario batches
- [backends.md](backends.md) — CPU / GPU and dispatch

## Building with FinIR
- [kernels.md](kernels.md) — the kernel library
- [agent-integration.md](agent-integration.md) — structured intent for AI systems
- [intent-contract.md](intent-contract.md) — **the canonical FinIR Intent Contract (v1.0)** — the schema the NL layer emits and the runtime consumes
- [huggingface-intent-handoff.md](huggingface-intent-handoff.md) — implementation summary for the Hugging Face intent workstream
- [extending.md](extending.md) — custom kernels, backends, templates
- [performance.md](performance.md) — benchmarks and honest caveats

## Research
- [../research/experiment_001_incremental_financial_reasoning.md](../research/experiment_001_incremental_financial_reasoning.md)
- [../research/experiment_002_backend_dispatch.md](../research/experiment_002_backend_dispatch.md)
- [../research/prior_art.md](../research/prior_art.md)
