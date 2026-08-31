# Scenarios & what-if

Financial AI performs repeated what-if analysis. FinIR makes it first-class and
incremental.

## Change specs

A change spec says how an input moves, compactly:

| Spec | Meaning |
|------|---------|
| `"+8%"` / `"-8%"` | relative change |
| `"30d->60d"` | absolute retarget (→ 60) |
| `500_000` | absolute set |
| `{"relative": 0.04}` | relative |
| `{"delta": 5}` | additive |
| `{"absolute": 60}` | set |

## What-if (single scenario, incremental)

```python
model.evaluate()  # warm the base
s = model.what_if(cogs="+4%")
s["ebitda"]
s.recomputed  # only cogs' downstream cone
s.reused  # everything else, from the base
```

## Named scenarios

```python
model.scenarios(
    {
        "base": {},
        "upside": {"revenue": "+10%"},
        "downside": {"revenue": "-8%", "cogs": "+5%"},
    }
)
```

Each scenario reuses the base for unaffected nodes.

## Large scenario batches (vectorized)

```python
import numpy as np

r = model.run_scenarios(cogs=np.linspace(300e6, 400e6, 1_000_000))
r["ebitda"].shape  # (1_000_000,)
r.stats.backend  # 'cpu' (or 'gpu' if a large batch + a device)
```

The batch is broadcast through the graph with NumPy (or CuPy on GPU). On this
project's reference machine, 1,000,000 arithmetic scenarios evaluate in tens of
milliseconds on CPU (see [performance.md](performance.md)).

## Agent iteration

`model.state()` + `with_change` chains snapshots for an agent's iterative reasoning,
each recording the inputs it changed — so the agent (and you) can see exactly what
each step dirtied.
