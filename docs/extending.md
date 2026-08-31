# Extending EIF

Most extensions plug into an existing extension point — no framework changes.

## Add an event type

```python
from eif.ontology import EVENT_REGISTRY, EventTypeDefinition
from eif.domain.enums import Direction

EVENT_REGISTRY.register(EventTypeDefinition(
    key="fx_exposure_change",
    label="FX Exposure Change",
    category="risk",
    default_metrics=["operating_income"],
    typical_direction=Direction.UNKNOWN,
    impact_strategy="generic",
))
```

Add entity types via `ENTITY_REGISTRY` and metrics via `METRIC_REGISTRY` the same
way.

## Add a connector

Subclass `EIFConnector`, implement `can_handle` and `load`, and register it. See
[connectors.md](connectors.md).

## Add a model provider

Implement the relevant interface (`LLMProvider`, `EmbeddingProvider`,
`VisionProvider`, `TranscriptionProvider`) and set `sends_data_offhost`. See
[providers.md](providers.md).

## Replace a pipeline stage

Every stage is injectable:

```python
from eif.pipeline import EIFPipeline
from eif.pipeline.stages import ObservationExtractor, ImpactEstimator

class MyExtractor(ObservationExtractor):
    def extract(self, evidence): ...

pipeline = EIFPipeline(
    repo,
    observation_extractor=MyExtractor(),
    impact_estimator=MyEstimator(),
)
```

Stage interfaces: `ObservationExtractor`, `EventCandidateGenerator`,
`ImpactEstimator`, `MaterialityEngine`, plus `EntityResolver` / `EventResolver`
for the graph.

## Add an impact strategy

Point an event type at a strategy name and implement it on a custom
`ImpactEstimator` (or add a `_strategy_<name>` method). It must return no impact
when its required inputs are missing — never a fabricated number. See
[impact-estimation.md](impact-estimation.md).

## Add a storage backend

Implement the `Repository` interface (see
[../src/eif/storage/base.py](../src/eif/storage/base.py)). The event graph, API,
and CLI all program against it, so a new backend (e.g. Neo4j) needs no changes
elsewhere.

## Add a benchmark case

Drop a case directory under `benchmarks/cases/` in the documented format, marked
synthetic. See [benchmark.md](benchmark.md).

## Custom event-bus adapter

Implement `EventBus` (`publish` / `subscribe` / `unsubscribe`) to bridge Kafka,
Redis Streams, NATS, or a cloud queue. The in-process implementation is the
reference.
