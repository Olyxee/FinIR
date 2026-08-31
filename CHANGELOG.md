# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-30

First public release — the initial serious release of EIF as open infrastructure.

### Added

- **Domain model**: typed, validated Pydantic objects for Evidence, Observation,
  Economic Entity, Economic Event, Economic Impact, Estimate/Confidence,
  Event Relationship, Realized Outcome, and mandatory Provenance.
- **Ontology registries**: extensible registries for event types (22+ built-in),
  entity types, and financial metrics.
- **Storage**: repository interface with an in-memory backend and a SQLAlchemy
  backend that runs identically on SQLite and PostgreSQL.
- **Event graph**: persistent graph with entity/event resolution and
  reinforce / weaken / contradict / resolve semantics.
- **Providers**: model-agnostic `LLMProvider`, `EmbeddingProvider`,
  `VisionProvider`, `TranscriptionProvider` interfaces; deterministic mock
  providers (default); optional OpenAI-compatible, Anthropic, and Gemini adapters.
- **Pipeline**: composable stages — extraction, entity resolution, candidate
  generation, deterministic impact estimation, materiality, integration.
- **Connectors**: reference connectors for text, email (.eml), JSON, CSV, Excel,
  PDF, audio, image, and directory ingestion; documented interface placeholders
  for email inbox, chat, CRM, ERP, database, and cloud storage.
- **Deterministic impact estimation** with per-event-type strategies and full
  calculation provenance.
- **Materiality engine** with absolute and relative thresholds.
- **Evaluation**: Economic Signal Lead Time (ESLT), detection precision/recall/F1,
  impact MAE/MAPE, interval coverage, and confidence calibration (ECE).
- **Benchmark framework**: open case format, eight synthetic scenarios, seeded
  variant generator, and a baseline-vs-EIF runner.
- **Reference research experiment** (`research/experiment_001.md`).
- **CLI** (`eif`): analyze, events, event, entities, outcome, doctor, serve, and
  benchmark commands.
- **API**: optional FastAPI service with versioned `/v1` endpoints, pagination,
  structured errors, and auto-generated OpenAPI.
- **Event bus**: in-process pub/sub with a documented adapter interface.
- **Ops**: Docker + docker-compose (optional PostgreSQL), GitHub Actions CI and
  release workflows, pre-commit configuration.
- **Docs**: concepts, architecture, economic events, observations, provenance,
  impact estimation, confidence, connectors, providers, deployment,
  configuration, security, privacy, evaluation, benchmark, and extending guides.

[Unreleased]: https://github.com/Lethabo-Scofield/economic-intelligence-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Lethabo-Scofield/economic-intelligence-framework/releases/tag/v0.1.0
