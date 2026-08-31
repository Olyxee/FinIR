# Provenance

Provenance is **mandatory** in EIF. Every observation, event, and impact carries a
`Provenance` record so you can always answer:

- What source produced this conclusion?
- When was the source created? Which model processed it, at which version?
- What deterministic calculations were used?
- Which assumptions were introduced?
- Which observations support this event? Which evidence contradicts it?

## What is (and isn't) stored

EIF stores **structured reasoning artifacts**, not raw model chain-of-thought:

| Artifact | Field | Purpose |
|----------|-------|---------|
| Citation | `citations` | Pointer into evidence (`evidence_id`, locator, snippet, stance). |
| Calculation | `calculations` | A deterministic formula with concrete inputs and result. |
| Assumption | `assumptions` | An interpretive assumption, its method, source, and confidence. |
| Decision | `decisions` | A pipeline decision (entity match, merge, …). |
| Metadata | `producer`, `method`, `model`, `model_version`, `framework_version`, `pipeline_run_id` | Who/what/when. |

Private model reasoning is deliberately **not** persisted.

## Reproducible numbers

Every number an impact reports has a `Calculation` recording exactly how it was
derived:

```python
Calculation(
    name="gross_spend_exposure",
    expression="annual_spend * pct / 100",
    inputs={"annual_spend": 42_000_000, "pct": 10},
    result=4_200_000,
    unit="ZAR",
)
```

Anyone can recompute `42_000_000 * 10 / 100 == 4_200_000`. This is why EIF does
arithmetic in code, not in the model.

## Tracing an event

```python
event = eif.get_event(event_id)
for c in event.provenance.citations:
    print(c.stance, c.evidence_id, c.locator)
impact = event.primary_impact()
for calc in impact.provenance.calculations:
    print(calc.expression, calc.inputs, "=", calc.result)
print("supports:", event.provenance.supporting_evidence_ids())
print("contradicts:", event.provenance.contradicting_evidence_ids())
```

Provenance records **merge** (not overwrite) when evidence reinforces an event, so
the trail accumulates over the event's life.
