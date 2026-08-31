# Concepts

EIF converts multimodal business evidence into standardized, machine-readable
economic events and their estimated financial consequences. The central idea:

> Recognize economic reality while it is still emerging — before it becomes a
> structured transaction, accounting entry, or KPI.

## The abstraction chain

```
Multimodal Business Evidence
  → Observations
    → Economic Events
      → Economic Consequences (Impacts)
        → Provenance
          → Feedback / Actual Outcome
```

Each arrow is a well-defined, replaceable pipeline stage.

## Core objects

| Object | What it is | Key module |
|--------|------------|------------|
| **Evidence** | Raw/normalized information entering the system (email, PDF, CSV, transcript, image, …). Root of all provenance. | `eif.domain.evidence` |
| **Observation** | A structured statement derived from evidence: claims + measurements + entities, with confidence and citations. | `eif.domain.observation` |
| **Economic Entity** | A named participant: supplier, customer, product, project, contract, … (extensible). | `eif.domain.entity` |
| **Economic Event** | The central object: a typed, versioned, persistent node with timing, magnitude, probability, confidence, impacts, and status. | `eif.domain.event` |
| **Economic Impact** | An estimated (and eventually realized) consequence on a financial metric, with an uncertainty interval and calculation provenance. | `eif.domain.impact` |
| **Event Relationship** | A typed edge between events (causes, contributes_to, contradicts, …). | `eif.domain.relationship` |
| **Realized Outcome** | What actually happened, plus when a conventional system detected it. Powers the feedback loop and ESLT. | `eif.domain.outcome` |
| **Provenance** | Mandatory audit trail: citations, deterministic calculations, assumptions, decisions. | `eif.domain.provenance` |

## Design principles

- **Model-agnostic.** Providers are swappable; the deterministic mock is the
  default so everything runs offline.
- **Deterministic math.** Numbers are computed in code, not by a model. Models
  handle interpretation only, validated against typed schemas.
- **Provenance is mandatory.** Every derived object traces back to evidence.
- **Uncertainty is explicit.** Estimates carry intervals, probability, and
  confidence — never presented as bare facts.
- **Extensible, not magic.** Open vocabularies (event types, entities, metrics)
  live in registries; pipeline stages are replaceable interfaces.

See [architecture.md](architecture.md) for how these fit together.
