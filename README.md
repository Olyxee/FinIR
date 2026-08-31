# Economic Intelligence Framework (EIF)

**Recognize economic consequences before they reach the ledger.**

EIF turns multimodal business evidence — documents, communications, operational
data, and financial records — into standardized **economic events** with
quantified impacts, uncertainty, timing, and provenance.

```
Business Evidence
      ↓
Observations
      ↓
Economic Events
      ↓
Financial Consequences
```

EIF is **open infrastructure**, not a website, dashboard, SaaS product, or
chatbot. It is model-agnostic, runs fully offline by default, does its arithmetic
deterministically in code, and traces every conclusion back to its evidence.

[![CI](https://github.com/Lethabo-Scofield/economic-intelligence-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/Lethabo-Scofield/economic-intelligence-framework/actions/workflows/ci.yml)
&nbsp;License: Apache-2.0 &nbsp;·&nbsp; Python 3.11+

---

## Why EIF exists

Businesses generate economically important information long before it appears in
financial systems:

- A supplier announces a future price increase in an **email**.
- A customer signals reduced orders on a **call**.
- A **contract** contains an upcoming obligation.
- A project **meeting** reveals a likely delay.
- Operational **data** shows inventory accumulating.

Traditional finance systems understand these consequences only *after* they become
structured transactions, accounting entries, or KPIs. By then the window to act
has narrowed. EIF provides the missing abstraction so you can **recognize economic
reality while it is still emerging.**

## What problem it solves

EIF gives you one standard representation for economic reality across every
modality, so downstream systems (risk, planning, FP&A, treasury) can consume a
single machine-readable stream of events and impacts instead of re-parsing emails,
PDFs, and spreadsheets themselves. It differs from BI/ERP (which report structured
history), from document AI (which extracts text, not economic consequence), and
from a chatbot (which produces prose, not typed, provenanced, quantified events).

## Architecture

```
  CLI  ─▶   EIF facade   ◀─ API (FastAPI, optional)
              │
   Connectors → Observation Extractor → Entity Resolution →
   Candidate Generation → Impact Estimation → Materiality →
   Event Graph Integration
              │
        Event Graph ─▶ Repository  (memory · SQLite · PostgreSQL)
```

Every stage is a replaceable interface. See [docs/architecture.md](docs/architecture.md).

## Quick start

> EIF is not yet published to PyPI. Install from source:

```bash
git clone https://github.com/Lethabo-Scofield/economic-intelligence-framework
cd economic-intelligence-framework
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the end-to-end example (fully offline, no API keys):

```bash
python examples/quickstart.py
```

Or use the CLI:

```bash
eif analyze examples/data/
eif events
eif doctor
```

_(Once published, installation will be `pip install economic-intelligence-framework`.)_

## Example

```python
from eif import EIF

eif = EIF()

result = eif.analyze([
    "supplier_email.txt",     # "...10% price increase on SKU-A, effective 1 November 2026"
    "master_agreement.txt",   # contract: affected products
    "purchase_history.csv",   # annual spend = R42,000,000
])

for event in result.events:
    print(event.event_type, event.primary_impact())
```

Produces one machine-readable economic event — with a **deterministic** impact
calculation and full provenance:

```json
{
  "event_type": "supplier_price_change",
  "status": "emerging",
  "confidence": 0.75,
  "effective_at": "2026-11-01",
  "impacts": [
    {
      "metric": "cost_of_goods_sold",
      "direction": "increase",
      "estimate": 4200000,
      "currency": "ZAR"
    }
  ]
}
```

The number is not guessed by a model — it is computed in code and recorded:
`annual_spend (42,000,000) × pct (10) / 100 = 4,200,000`.

## Economic Event specification

An `EconomicEvent` is a typed, versioned, persistent node with entities, timing
(`detected_at` / `effective_at`), magnitude, probability, calibrated confidence,
affected metrics, estimated `impacts` (each an interval, not a bare number),
assumptions, materiality, status, and mandatory provenance. Event types are an
**open registry** (22+ built-in). Full spec: [docs/economic-events.md](docs/economic-events.md).

## Multimodal architecture

Connectors normalize every source into a common `Evidence` format:

- **Reference (offline):** text, email (`.eml`), JSON, CSV, Excel, PDF, audio,
  image, directory.
- **Integration placeholders (typed interfaces):** email inbox, Slack/Teams, CRM,
  ERP, database, cloud storage — real interfaces, no fake implementations.

Deterministic extraction pulls money, percentages, durations, dates, entities, and
table sums out of evidence — conservatively, never guessing. See
[docs/connectors.md](docs/connectors.md), [docs/observations.md](docs/observations.md).

## Evaluation & ESLT

EIF's headline metric is **Economic Signal Lead Time (ESLT)**:

```
ESLT = traditional_detected_at − eif_detected_at   (days; positive = EIF earlier)
```

It also reports detection precision/recall/F1, impact MAE/MAPE, interval coverage,
false-positive rate, and confidence calibration (ECE). See
[docs/evaluation.md](docs/evaluation.md).

## Model providers

Model-agnostic by design. The default is a **deterministic mock** provider, so
everything runs and is tested offline. Optional adapters: OpenAI /
OpenAI-compatible (Azure, vLLM, Ollama), Anthropic, Gemini. Models handle
*interpretation only*; numbers stay in code. See [docs/providers.md](docs/providers.md).

## Privacy

EIF runs fully local by default (mock provider, local embeddings, SQLite). Set
`private_mode: true` and any attempt to send evidence off-host raises an error.
Point an OpenAI-compatible provider at a local endpoint to use models without
leaving your network. See [docs/privacy.md](docs/privacy.md).

## Production deployment

```bash
docker compose up                # API on SQLite
docker compose --profile pg up   # API on PostgreSQL
curl http://localhost:8000/health
```

Same code and schema on SQLite (dev) and PostgreSQL (prod) — change one URL. The
optional FastAPI service exposes versioned `/v1` endpoints with pagination,
structured errors, and auto-generated OpenAPI. See [docs/deployment.md](docs/deployment.md).

## Extending EIF

Add event types, connectors, providers, impact strategies, storage backends, or
benchmark cases — all through existing extension points, no framework changes. See
[docs/extending.md](docs/extending.md).

## Benchmark

```bash
eif benchmark generate benchmarks/cases
eif benchmark report --cases benchmarks/cases   # baseline vs EIF
```

Ships an open case format and eight synthetic scenarios (all labeled synthetic).
See [docs/benchmark.md](docs/benchmark.md).

## Research

A reproducible reference experiment asks: *does multimodal business evidence
identify material events earlier or more accurately than structured data alone?*

```bash
python research/reproduce_experiment_001.py
```

On the synthetic suite, adding text/document evidence raised material-event
**recall from 0.14 → 1.00** with no loss of precision and a **median ~57-day**
lead over the modeled conventional indicator. These results demonstrate the
mechanism and methodology on **synthetic** data — not a real-world efficacy claim.
The writeup reports limitations honestly: [research/experiment_001.md](research/experiment_001.md).

## Roadmap

- Stronger reference extractors (model-assisted, validated) and evaluation on real,
  anonymized cases.
- Embedding-based entity/event resolution behind the existing interfaces.
- Event-bus adapters (Kafka, Redis Streams, NATS) behind the existing `EventBus`.
- Native graph-DB repository adapter (Neo4j) behind the existing `Repository`.
- Alembic migration recipes for managed Postgres deployments.
- More impact strategies and event types.

## Contributing

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Quality gates:
`ruff check`, `ruff format --check`, `mypy`, `pytest` (CI runs all on 3.11–3.13).
Please keep data synthetic and results honest.

## Citation

If you use EIF in research, please cite it (see [CITATION.cff](CITATION.cff)):

```
EIF Contributors. Economic Intelligence Framework (EIF), v0.1.0, 2026.
https://github.com/Lethabo-Scofield/economic-intelligence-framework
```

## Acknowledgements

This project's research direction was inspired in part by work such as
**OmniScientist** and the broader movement toward omni-modal scientific reasoning.
EIF is an **independent** framework: it contains no OmniScientist code and has no
OmniScientist runtime dependency.

## License

Apache-2.0 — see [LICENSE](LICENSE).
