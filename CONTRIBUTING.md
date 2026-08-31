# Contributing to FinIR

Thank you for considering a contribution. FinIR aims to be a **small, serious
systems project**: a compiler/runtime target for financial computation. Contributions
that keep it small, correct, and honest are very welcome.

## Ground rules

- **CPU-first, no network for core tests.** The framework must remain fully usable on
  a CPU-only machine with no optional dependencies.
- **No fabricated performance.** Benchmark scripts must execute real code and write
  measured results. Never hard-code numbers. If GPU hardware is unavailable, report
  GPU performance as unverified — do not invent it.
- **No hype in the repo.** Do not add "world's first", "revolutionary", or
  "breakthrough". Novelty claims stay hypotheses until a prior-art review supports
  them (see `research/prior_art.md`).
- **No fake complexity.** No Kubernetes, auth, billing, dashboards, microservices,
  databases, or ERP/CRM connectors unless the runtime genuinely needs them.

## Development setup

```bash
git clone https://github.com/Lethabo-Scofield/finir
cd finir
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gates (run before a PR)

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

All four must pass. CI runs them on Python 3.11, 3.12, and 3.13 (CPU only).

## Extending FinIR

Most contributions plug into an existing seam — see [docs/extending.md](docs/extending.md):

| Add… | How |
|------|-----|
| a **kernel** | `@finir.kernel(...)` |
| a **backend** | subclass `ExecutionBackend` |
| a **stdlib template** | a function that adds nodes to a model |
| a **compiler pass** | add to `finir.compiler.passes` + the pipeline |
| a **benchmark** | add to `finir.benchmark`, write results to `benchmarks/results/` |

## Conventions

- One logical change per PR; add or update tests for any behavior change.
- Update `docs/` when public behavior changes.
- Keep the IR JSON schema backward-compatible, or bump `IR_SCHEMA_VERSION`.

## Security

Please report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## License

By contributing you agree your contributions are licensed under Apache-2.0.
