# Publishing FinIR to PyPI

How FinIR is packaged and released. The release is automated via GitHub Actions
using **PyPI Trusted Publishing (OIDC)** — no API tokens are stored in the repo.

## Package structure

- Source layout: `src/finir/` (src layout; the wheel installs the `finir` package).
- **Single version source:** `src/finir/version.py` → `__version__`. `pyproject.toml`
  declares `dynamic = ["version"]` with `[tool.hatch.version] path = "src/finir/version.py"`.
- **Package data:** the canonical intent schema `finir/intent/finir-intent-v1.schema.json`
  ships in the wheel (`[tool.hatch.build.targets.wheel] artifacts`) and is loaded at
  runtime with `importlib.resources` — never a repo-relative path. A byte-identical
  copy lives at `schemas/finir-intent-v1.schema.json` for external consumers; a test
  enforces no drift.
- **Runtime deps:** `numpy`, `typer`, `rich` (the CLI is first-class). Extras:
  `gpu` (CuPy), `viz` (Graphviz), `dev` (tooling). GPU is never required.
- **Entry point:** `finir = "finir.cli.main:main"`.

## Build locally

```bash
python -m build          # -> dist/finir-<v>.tar.gz and dist/finir-<v>-py3-none-any.whl
twine check dist/*       # metadata + README render check
```

## Local clean-install validation (do this before every release)

```bash
python -m venv /tmp/finir-wheel && . /tmp/finir-wheel/bin/activate   # Windows: \Scripts\activate
pip install dist/finir-<v>-py3-none-any.whl
cd /tmp                                   # leave the repo so imports come from the wheel
python -c "import finir; print(finir.__version__)"
finir --help && finir doctor
python -c "from finir import FinancialModel; m=FinancialModel(); m.input('revenue',5e8,currency='ZAR'); m.input('cogs',3e8,currency='ZAR'); m.define('gp','revenue-cogs',output=True); print(m.evaluate().values)"
python -c "from finir.intent import json_schema; print(json_schema()['title'])"
deactivate
```

Repeat with the sdist: `pip install dist/finir-<v>.tar.gz`.

## TestPyPI (recommended dry run)

TestPyPI is a separate index for rehearsing a release.

1. Configure a **TestPyPI Trusted Publisher** (see below) and a `testpypi` GitHub
   environment.
2. Run the Release workflow manually: **Actions → Release → Run workflow**, input
   `target = testpypi`. It builds and publishes to TestPyPI.
3. Verify in a fresh env. Because FinIR's dependencies (NumPy, Typer, Rich) live on
   real PyPI, point pip at both indexes:

   ```bash
   pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ finir
   ```

## Trusted Publishing setup (one-time, manual on the PyPI website)

This step **cannot be done from CI or the CLI** — an owner must do it on the web:

1. Create the project's Trusted Publisher on PyPI:
   **https://pypi.org/manage/account/publishing/** → *Add a new pending publisher*:
   - PyPI Project Name: `finir`
   - Owner: `Olyxee`
   - Repository name: `finir`
   - Workflow name: `release.yml`
   - Environment name: `pypi`
2. (Optional) Repeat on **https://test.pypi.org/manage/account/publishing/** with
   environment `testpypi` for TestPyPI dry runs.
3. In GitHub: **Settings → Environments** → create `pypi` (and `testpypi`). Add
   required reviewers/branch restrictions if you want a manual approval gate.

Until step 1 is done, the publish job will fail with an OIDC/authorization error —
that is expected. Nothing else about the release needs a token.

## Cutting a release

```bash
# 1. bump src/finir/version.py, update CHANGELOG.md, commit on main
# 2. tag and push
git tag v0.1.0
git push origin v0.1.0
# 3. create a GitHub Release for the tag (UI, or:)
gh release create v0.1.0 --title "FinIR 0.1.0" --notes-file docs/release-notes-0.1.0.md
```

Publishing the GitHub Release triggers `release.yml`: it runs the quality gate,
builds sdist+wheel once, `twine check`s them, publishes to PyPI via Trusted
Publishing, and attaches the same files to the Release.

## Rollback & version immutability

- **PyPI versions are immutable.** A file for a given version can never be
  re-uploaded, even after deletion. If a release is broken:
  - **Yank** it on PyPI (hides it from new installs but keeps existing pins working).
  - Fix, bump to the next patch (`0.1.1`), and release again.
- Never try to "overwrite" a version. Always move forward.

## Releasing 0.1.1 later

1. Edit `src/finir/version.py` → `__version__ = "0.1.1"`.
2. Add a `## [0.1.1]` section to `CHANGELOG.md`.
3. Run the full [release checklist](release-checklist.md).
4. Tag `v0.1.1`, create the GitHub Release — the workflow does the rest.
