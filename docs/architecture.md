# Architecture

EIF is a library first, with an optional API and CLI on top. Everything is
composed from small, replaceable parts.

## Layers

```
          ┌─────────────────────────────────────────────┐
  CLI  ───▶            EIF facade (eif.EIF)              ◀─── API (FastAPI)
          └───────────────────┬─────────────────────────┘
                              │
        ┌──────────────────── Pipeline ────────────────────┐
        │ Connectors → Observation Extractor → Entity       │
        │ Resolution → Candidate Generation → Impact        │
        │ Estimation → Materiality → Graph Integration      │
        └───────────────────┬───────────────────────────────┘
             providers │     │ ontology (event/entity/metric registries)
        ┌──────────────▼─────▼───────────────┐
        │  Event Graph  ──▶  Repository       │  (memory | SQLite | Postgres)
        └────────────────────────────────────┘
```

## The pipeline

`EIFPipeline.process_evidence` runs these stages (each injectable):

1. **Persist evidence** — store the immutable source with its content hash.
2. **Extract observations** — deterministic signal extraction (money, %,
   durations, dates, entities, tables) → `Observation`s with citations.
3. **Resolve entities** — collapse duplicates to canonical entities; rewrite refs.
4. **Generate candidates** — rule-based mapping of observations → candidate
   `EconomicEvent`s, grouped so conflicting signals stay separate.
5. **Estimate impact** — per-event-type deterministic strategies compute numbers
   with full calculation provenance (or *no* number if inputs are missing).
6. **Assess materiality** — absolute/relative thresholds classify each event.
7. **Integrate into the graph** — event resolution decides new vs
   reinforce/weaken/contradict/resolve; persists the result.

See [economic-events.md](economic-events.md), [observations.md](observations.md),
[impact-estimation.md](impact-estimation.md).

## The event graph

Events persist across runs. New evidence updates existing events in place rather
than creating duplicates. `EventGraph` sits over the `Repository` interface, so it
works identically on the in-memory and SQL backends and could be re-implemented on
a native graph database behind the same interface. See
[../src/eif/graph/graph.py](../src/eif/graph/graph.py).

## Storage

One `Repository` interface, two backends:

- **MemoryRepository** — zero-dependency, for tests and quick use.
- **SqlRepository** — SQLAlchemy, document-in-relational layout, identical on
  SQLite and PostgreSQL. See [deployment.md](deployment.md).

## Providers

Four capability interfaces (`LLMProvider`, `EmbeddingProvider`, `VisionProvider`,
`TranscriptionProvider`). Deterministic mocks are the default; OpenAI-compatible,
Anthropic, and Gemini adapters are optional. See [providers.md](providers.md).

## What EIF is not

Not a website, dashboard, SaaS product, or chatbot. No frontend, auth UI, billing,
or fake integrations. It is infrastructure other systems build on.
