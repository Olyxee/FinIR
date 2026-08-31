# Agent integration

FinIR is designed to be an **execution target** for AI systems reasoning about
finance. The division of labour: the model *interprets*, the runtime *computes*.

```
natural-language / agent intent
        │  (optional interpretation layer)
        ▼
structured financial intent   { "operation": "relative_change", "target": "cogs", "value": 0.04 }
        │
        ▼
FinIR mutation + incremental execution
        ▼
deterministic financial result
```

## Structured intent (core)

Core FinIR consumes **structured** intent — no natural-language parsing inside the
core. `apply_intent` accepts:

```python
model.apply_intent({"operation": "relative_change", "target": "cogs", "value": 0.04})
model.apply_intent({"operation": "set", "target": "revenue", "value": 5.2e8})
model.apply_intent({"operation": "delta", "target": "opex", "value": -5e6})
```

Each returns an `EvaluationResult` with `recomputed` / `reused` so the agent can see
what its change affected.

## Optional intent compiler (interpretation layer)

Natural-language interpretation is an **optional** layer implementing `IntentCompiler`:

```python
from finir import MockIntentCompiler

compiler = MockIntentCompiler()  # deterministic, offline, no LLM
intent = compiler.compile("What happens if COGS increases 4%?")
# -> {"operation": "relative_change", "target": "cogs", "value": 0.04}
result = model.apply_intent(intent)
```

`MockIntentCompiler` is dependency-free so examples and tests run offline. A real
LLM-backed compiler implements the same one-method interface behind an extra — the
model interprets, the runtime computes.

## Why not just generate Python?

Because generated code is non-deterministic, unaudited, re-executes everything each
turn, and can silently mix currencies or units. Structured intent over a typed IR is
deterministic, type-checked, incrementally executed, and inspectable. See the
runnable [`examples/agent_financial_reasoning/`](../examples/agent_financial_reasoning/run.py).
