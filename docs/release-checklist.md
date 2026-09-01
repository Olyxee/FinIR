# FinIR release checklist

A reusable, copy-per-release checklist. Tick each box before tagging. Details and
commands are in [pypi-release.md](pypi-release.md).

## Pre-flight (on `main`, clean tree)

- [ ] Version updated in `src/finir/version.py` (the single source; `pyproject.toml`
      reads it via `[tool.hatch.version]`).
- [ ] `CHANGELOG.md` has a dated section for this version.
- [ ] `ruff check .` green
- [ ] `ruff format --check .` green
- [ ] `mypy src` green
- [ ] `pytest -q` green (record the count)
- [ ] `python -m build` produces `dist/finir-<v>.tar.gz` and `dist/finir-<v>-py3-none-any.whl`
- [ ] `twine check dist/*` green
- [ ] Wheel clean-install tested in a fresh venv (import, `__version__`, CLI, doctor)
- [ ] sdist clean-install tested in a fresh venv (same checks)
- [ ] README quick-start example runs against the installed package
- [ ] Intent schema loads from the **installed** package (`finir.intent.json_schema()`)
      and `model.apply_intent(...)` works — not via the repo's `schemas/` dir
- [ ] CLI verified: `finir --help`, `finir doctor`, `finir benchmark --help`
- [ ] Benchmark run recorded (`finir benchmark --full`) — do not edit results
- [ ] Cross-platform CI green on GitHub (Linux/macOS/Windows × 3.11–3.13)

## Publish

- [ ] TestPyPI dry run (optional but recommended): `workflow_dispatch` → `testpypi`,
      then `pip install -i https://test.pypi.org/simple/ finir` in a fresh venv
- [ ] PyPI **Trusted Publisher** configured for `Olyxee/finir` (one-time; see
      pypi-release.md) and a `pypi` GitHub environment exists
- [ ] Git tag created: `git tag v<v> && git push origin v<v>`
- [ ] GitHub Release created for the tag (this triggers the publish workflow)
- [ ] Release workflow succeeded → published to PyPI + wheel/sdist attached to the release
- [ ] `pip install finir==<v>` verified in a fresh environment outside the repo

## Notes

- PyPI versions are **immutable** — a version can never be re-uploaded. If something
  is wrong, yank it and release a new patch (e.g. `0.1.1`).
- The workflow builds **once** and publishes the same artifacts to PyPI and the
  GitHub Release — do not build separate artifacts by hand.
