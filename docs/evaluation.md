# Evaluation

EIF ships honest, reproducible evaluation. All metrics live in `eif.evaluation`.

## Economic Signal Lead Time (ESLT)

The headline metric. How much earlier does EIF identify an economically meaningful
event than a conventional structured indicator?

```
ESLT = traditional_detected_at − eif_detected_at   (days)
```

Positive ESLT means EIF was earlier. It is only defined for events EIF detected
and for which a traditional-detection timestamp is known (recorded on the realized
outcome). `compute_eslt` reports per-event values plus mean, median, stdev,
min/max, a 95% CI (normal approximation), and the fraction positive.

```python
from eif.evaluation import compute_eslt, ESLTRecord
summary = compute_eslt(records)
print(summary.as_dict())
```

## Detection metrics

`match_events(predicted, gold)` matches a predicted event to a gold label when
they share an event type and at least one entity name. From the matching:

- **precision / recall / F1**
- **false positive rate**

Only material predictions are scored, so non-material events are never counted as
false alarms.

## Impact metrics

`impact_metrics(matched)` reports:

- **MAE** and **MAPE** of the point estimate,
- **interval coverage** — did the realized/gold value fall inside `[lower, upper]`?

The benchmark distinguishes two impact views:

- *vs label* — reproduces the intended deterministic estimate (checks reproducibility);
- *vs realized outcome* — the honest predictive-accuracy figure.

## Calibration

`calibration_error(confidences, correct)` computes **ECE** over equal-width bins —
do confidence-0.8 events turn out real ~80% of the time?

## Feedback loop

Record what actually happened to reconcile estimates and populate ESLT:

```python
from eif.domain import RealizedOutcome
eif.record_outcome(RealizedOutcome(
    event_id=event.id,
    realized_metrics={"cost_of_goods_sold": 3_900_000},
    traditional_detected_at=some_date,
    traditional_source="AP variance review",
))
```

See [benchmark.md](benchmark.md) and the reference experiment in
[../research/experiment_001.md](../research/experiment_001.md).
