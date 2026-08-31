# The compiler

FinIR has a small pass pipeline over the IR. Some passes transform the module,
others only analyse it; the pipeline threads a `CompileReport` so
`finir compile model.finir --show-passes` shows exactly what each did.

```python
from finir import parse, compile_model

compiled = compile_model(parse(open("model.finir").read()))
```

## Passes

| Pass | Kind | What it does |
|------|------|--------------|
| `validation` | analysis | references resolve, no cycles, outputs exist |
| `type_check` | analysis | infer + assign a `FinType` to every node |
| `constant_folding` | transform | fold constant subexpressions (and constant-only kernels) into literals |
| `common_subexpression_elimination` | transform | hoist repeated leaf subexpressions into shared nodes (conservative, no nesting) |
| `dead_node_elimination` | transform | drop nodes not reachable from outputs |
| `dependency_pruning` | analysis | reachability report |
| `scenario_vectorization` | analysis | mark pure-arithmetic (vectorizable) nodes |
| `kernel_fusion` | analysis | identify fusable arithmetic chains (see note) |
| `cache_planning` | analysis | count cacheable nodes and inputs |

## A note on fusion (honesty)

The fusion pass currently **identifies** fusable arithmetic chains but does not emit
a fused kernel. NumPy already fuses elementwise operations internally, so a separate
FinIR fusion kernel showed **no material CPU speedup** in our measurements. We keep
the analysis (and say so plainly) rather than ship complexity that does not pay for
itself. See [performance.md](performance.md).

## Interactive vs. ahead-of-time

The live `FinancialModel` engine runs only `validate` + `type_check` so that **all**
user node names remain queryable — DCE/CSE (which add/remove nodes) run in the
`finir compile` ahead-of-time path, not under the interactive model.

## Debugging

```
finir compile model.finir --show-passes
```

prints a table of pass, time, and a per-pass detail summary.
