# The incremental runtime

The `IncrementalEngine` is FinIR's reason to exist: it evaluates a module while
recomputing **only** the nodes affected by a change and reusing everything else in
O(1).

## How it works

The engine keeps a persistent value store and a *validity* set:

- `set_input(name, value)` records the value and **invalidates that input's
  downstream cone** (transitive dependents), using a precomputed dependents
  adjacency — an O(changed cone) operation.
- `evaluate(targets)` walks the needed nodes in dependency order: if a node is still
  valid, reuse its stored value (a dict lookup); otherwise recompute via the backend
  and mark it valid.

This dirty-set propagation is why incremental is actually cheaper than full
recompute: **reuse costs a lookup, not a re-derived cache key**. (An earlier
signature-per-node design was *slower* than recompute for cheap graphs — see
[performance.md](performance.md) for that honest story.)

## What you get back

`evaluate` returns an `EvaluationResult`:

```python
r = model.evaluate()
r["ebitda"]  # output value
r.recomputed  # nodes recomputed this run
r.reused  # nodes reused from cache
r.stats.as_dict()  # backend, time, nodes_evaluated, nodes_reused, hit ratio, memory
```

## Scenario (transient) evaluation

`what_if` / `scenarios` evaluate against the persistent base **without disturbing
it**: the changed inputs' cone is recomputed with the overridden values, and every
other node is read from the base store. So an unaffected node is reused even under a
different scenario.

## State snapshots

`model.state()` returns an immutable `ModelState`; `with_change` chains changes and
records which inputs moved, giving an agent a clean, inspectable trail
(`evaluate_state` runs one).

## Concurrency

Scenario batches are pure array operations (safe to parallelize at the caller
level). The engine itself is single-threaded per instance; run independent models in
independent threads/processes. FinIR deliberately avoids a heavy concurrency
framework.
