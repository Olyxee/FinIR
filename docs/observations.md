# Observations

An `Observation` is the bridge between raw evidence and economic events: a
structured statement derived from one or more pieces of evidence. Observations are
event-agnostic — the same observation may feed several candidate events.

## Structure

- `evidence_ids` — the evidence this observation was derived from.
- `observed_at` / `effective_at` — when it was observed and when the condition
  takes effect (if known).
- `entities` — `EntityRef`s found in the evidence, with roles.
- `claims` — natural-language assertions (the salient sentences).
- `measurements` — numeric facts: `percent`, `money` (with a context label such as
  `spend`/`revenue`/`penalty`), `duration_days`, `table_sum`, `row_count`.
- `confidence`, `extraction_method`, `model` — how it was produced and how much to
  trust it.
- `provenance` — citations back into the evidence.

## Deterministic extraction

The default `DeterministicObservationExtractor` uses transparent, tested rules in
[`eif.pipeline.signals`](../src/eif/pipeline/signals.py):

- **Money**: `R4.2m`, `ZAR 42,000,000`, `$1.8m`, `R850k`, and labeled amounts like
  `annual_spend: 42000000` — each tagged with an inferred context label.
- **Percentages**, **durations** (`3 weeks` → 21 days), **directions**
  (increase/decrease), **effective dates** (absolute and relative).
- **Entities**: supplier/customer/project/product/contract/order mentions.
- **Tables**: per-column sums for money/quantity columns in rendered CSV/Excel.

The extractor is **conservative**: it prefers extracting nothing to guessing, so
downstream estimates are never fabricated.

## Model-assisted extraction (optional)

`LLMObservationExtractor` wraps the deterministic extractor and asks a model for
*one extra claim* of interpretation. The model never supplies numbers — those stay
deterministic — and its output is merged, not trusted blindly. Swap it in via the
pipeline:

```python
from eif.pipeline import EIFPipeline, LLMObservationExtractor
from eif.providers import build_llm_provider
from eif.config import ModelRole

pipeline = EIFPipeline(
    repo,
    observation_extractor=LLMObservationExtractor(build_llm_provider(ModelRole(provider="mock"))),
)
```
