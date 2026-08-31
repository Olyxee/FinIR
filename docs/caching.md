# Caching

FinIR reuses a node's value whenever every input feeding it is unchanged. Reuse is
tracked by a **validity set** over the persistent value store: changing an input
invalidates its downstream cone; nodes outside that cone stay valid and are reused.

## Correctness

A node is reused only when it is still valid, and validity is cleared for exactly
the transitive dependents of any changed input. So a stale value can never leak
across a changed input — the invariant the finance domain requires.

## Metrics

```python
model.evaluate()
model.what_if(cogs="+4%")
model.cache_stats()
# {'hits': 12, 'misses': 16, 'recomputed': 16, 'reused': 12, 'hit_ratio': 0.43}
```

and per-run detail on `result.stats`:

```
nodes_evaluated   nodes recomputed this run
nodes_reused      nodes served from cache
cache_hit_ratio   cumulative reuse ratio
memory_estimate_bytes
```

## Scenario cache keys

Scenario (`what_if`) evaluation reuses the persistent base values for every node
outside the changed cone. Large scenario **batches** (arrays) are evaluated fresh
rather than reused, because an array override changes the value space of the whole
batch — reusing a scalar base for an array node would be wrong. This is a
deliberate, documented choice: incremental reuse targets the *interactive
single-change* pattern; batch execution targets throughput.

## Design history (honesty)

An earlier version keyed the cache by a per-node signature (a tuple over the node's
transitive input versions). It was *correct* but rebuilding those signatures each
evaluation cost more than the trivial arithmetic it saved — making "incremental"
slower than full recompute on large cheap graphs. The current validity-set design
replaced it; see [performance.md](performance.md).
