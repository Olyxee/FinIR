# Contributing to EIF

Thank you for considering a contribution to the Economic Intelligence Framework.
EIF aims to be **boring, reliable infrastructure**: composable, explicit, and
honest. Contributions that keep it that way are very welcome.

## Ground rules

- **No secrets or real data.** Never commit credentials, API keys, or real
  customer/financial data. All example and benchmark data must be synthetic and
  clearly labeled as such.
- **Determinism first.** Numeric results should be computed in code, not by a
  model. If a model is involved, its output must be validated against a typed
  schema and its influence documented.
- **Research integrity.** Do not tune labels or hide unfavorable results. If EIF
  performs worse in a case, report it (see `research/experiment_001.md`).

## Development setup

```bash
git clone https://github.com/Lethabo-Scofield/economic-intelligence-framework
cd economic-intelligence-framework
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gates (run before opening a PR)

```bash
ruff check src tests
ruff format --check src tests
mypy
pytest
```

All four must pass. CI runs them on Python 3.11, 3.12, and 3.13.

## Extending EIF

Most contributions plug into an existing extension point — no framework changes
needed:

| You want to add…            | Do this                                                        |
|-----------------------------|----------------------------------------------------------------|
| A new **event type**        | `EVENT_REGISTRY.register(EventTypeDefinition(...))`             |
| A new **connector**         | Subclass `EIFConnector`, register it in a `ConnectorRegistry`  |
| A new **model provider**    | Implement `LLMProvider` / `EmbeddingProvider` / etc.           |
| A new **impact strategy**   | Add a `_strategy_<name>` method / custom `ImpactEstimator`     |
| A new **benchmark case**    | Add a case dir under `benchmarks/cases/` (mark it synthetic)   |

See `docs/extending.md` for details and examples.

## Commit / PR conventions

- Keep PRs focused; one logical change per PR.
- Add or update tests for any behavior change.
- Update `docs/` and `README.md` when public behavior changes.
- Fill in the PR template checklist.

## Reporting security issues

Please **do not** open a public issue for vulnerabilities. Follow the process in
[SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the
Apache-2.0 License (see [LICENSE](LICENSE)).
