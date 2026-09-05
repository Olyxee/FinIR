# FinIR 0.1.1: documentation-only patch

**No changes to `finir`'s code, public API, or runtime behavior** — every file under
`src/finir/` is byte-identical to `0.1.0` (verified via `git diff v0.1.0..v0.1.1 --
src/finir/`, zero diff). This release exists solely to refresh the README PyPI
displays: PyPI renders the README bundled with a given version at upload time and
never updates it from GitHub changes on its own, so the `0.1.0` project page was
showing a stale README.

## Changed

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

```bash
pip install --upgrade finir
```
