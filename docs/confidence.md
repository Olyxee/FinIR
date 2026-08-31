# Confidence & Uncertainty

EIF keeps uncertainty explicit and refuses to present uncertain estimates as
facts. Two complementary primitives (`eif.domain.confidence`):

## `Confidence` — belief that something is real

A score in `[0, 1]`, decomposed into inspectable factors:

```python
Confidence.combine(
    model_confidence=0.9,
    evidence_strength=0.95,
    conflict_penalty=0.05,
)
# score = 0.9 * 0.95 * (1 - 0.05) = 0.812
```

The combination is a simple, transparent product — not a hidden learned function —
so you can see exactly why a belief is what it is, and re-weight it yourself.

In the graph, reinforcing evidence combines confidences with **noisy-OR**
(`1 - (1-a)(1-b)`); contradicting evidence applies a **conflict penalty**.

## `Estimate` — a number with an interval

```json
{
  "point": 4200000,
  "lower": 3300000,
  "upper": 5100000,
  "unit": "ZAR",
  "probability": 0.9,
  "confidence": 0.81
}
```

- `probability` — the chance the underlying event occurs at all.
- `confidence` — how much to trust the estimate given the event occurs.
- `expected_value` = `point * probability`.
- Invariant (enforced): `lower <= point <= upper`.

## Calibration

The evaluation module reports **Expected Calibration Error (ECE)** — do events at
confidence ~0.8 actually turn out real ~80% of the time? See
[evaluation.md](evaluation.md). Track it against realized outcomes to know whether
your confidences mean anything.

## Principle

Never collapse a range to a point silently. Downstream consumers should see the
interval, the probability, and the confidence, and decide their own risk posture.
