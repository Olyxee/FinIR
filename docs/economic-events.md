# Economic Events

The `EconomicEvent` is the central object of EIF: a typed, versioned, persistent
node in the event graph.

## Fields

| Field | Meaning |
|-------|---------|
| `id`, `version` | Identity and monotonically increasing version (bumped on every in-place update). |
| `event_type` | Registered event-type key (see the registry below). |
| `title`, `organization_id` | Human label and tenancy. |
| `status` | `emerging` → `confirmed` / `weakened` → `resolved` / `dismissed` / `superseded`. |
| `materiality` | `material` / `non_material` / `unknown`. |
| `entities` | Entity references with roles (supplier, affected_product, …). |
| `observation_ids`, `evidence_ids` | Everything supporting the event. |
| `detected_at`, `effective_at`, `expected_resolution_at`, `resolved_at` | Timing. |
| `magnitude`, `magnitude_unit` | Primary magnitude (e.g. a percentage). |
| `probability`, `confidence` | Likelihood and calibrated belief. |
| `affected_metrics`, `impacts` | Financial metrics and estimated consequences. |
| `assumptions`, `provenance` | Interpretive assumptions and the full audit trail. |

## Event-type registry

Event types are an **open vocabulary** in `EVENT_REGISTRY`. Built-in types include
`supplier_price_change`, `demand_change`, `supply_disruption`,
`customer_expansion`, `customer_contraction`, `contract_obligation`,
`payment_delay`, `collection_risk`, `project_delay`, `cost_overrun`,
`capacity_change`, `inventory_accumulation`, `inventory_shortage`,
`asset_failure_risk`, `regulatory_change`, `workforce_change`,
`revenue_opportunity`, `revenue_risk`, `liquidity_pressure`, `margin_pressure`,
and more.

Each `EventTypeDefinition` declares the metrics it typically affects, its usual
direction, and an impact strategy. Register your own:

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

## Lifecycle in the graph

New evidence does not spawn duplicates. The event resolver matches a candidate to
an existing open event of the same type sharing an entity within a time window,
then the graph applies:

- **reinforce** — raise confidence (noisy-OR), attach evidence, mark `confirmed`;
- **contradict** — apply a conflict penalty, record contradicting citations, mark
  `weakened`;
- **resolve** — close the event when its outcome is known.

See [../src/eif/graph/resolution.py](../src/eif/graph/resolution.py).

## Example output

```json
{
  "event_type": "supplier_price_change",
  "status": "emerging",
  "confidence": 0.75,
  "effective_at": "2026-11-01",
  "impacts": [
    {"metric": "cost_of_goods_sold", "direction": "increase",
     "estimate": 4200000, "currency": "ZAR"}
  ]
}
```
