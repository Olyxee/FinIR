# Backends & dispatch

A backend decides *how* a node's arithmetic runs. The engine owns the graph,
caching, and scheduling; the backend owns the numeric representation.

## Backends

| Backend | Module | When |
|---------|--------|------|
| `NumpyBackend` (name `cpu`) | `backends.numpy_backend` | always — reference + vectorized CPU |
| `GpuBackend` (name `gpu`) | `backends.gpu` | optional (`pip install finir[gpu]`), if a CUDA device is present |

`NumpyBackend` handles both scalar graphs and large scenario batches (arrays)
through NumPy broadcasting — no special vector code. It is the default and requires
nothing beyond NumPy.

## GPU

The GPU backend uses CuPy. It accelerates **arithmetic-graph scenario batches**;
named kernels (NPV, risk) are evaluated on the host and their results moved back to
the device, so correctness never depends on a GPU implementation of every kernel.
GPU is never required — `gpu_available()` is safe to call anywhere and returns
`False` on CPU-only machines.

## Dispatch (cost model)

`BackendPlanner.choose(WorkloadProfile(scenario_size=N))`:

```
scalar graph / small batch      -> CPU (scalar or vectorized)
very large batch + GPU present  -> GPU
very large batch, no GPU        -> vectorized CPU
```

The GPU threshold (`GPU_MIN_ELEMENTS`, default 250,000) is a **heuristic** to be
calibrated on real GPU hardware — see
[../research/experiment_002_backend_dispatch.md](../research/experiment_002_backend_dispatch.md).
Override explicitly when you want to:

```python
model.evaluate(backend="cpu")
model.run_scenarios(cogs=grid, backend="gpu")
```

## CPU-first

The first release is fully usable on CPU-only machines. On the reference machine,
1,000,000 arithmetic scenarios run in tens of milliseconds on CPU. GPU is an
optional accelerator for very large batches, not a requirement.
