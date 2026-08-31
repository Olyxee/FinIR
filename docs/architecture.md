# Architecture

FinIR is a small stack of cleanly separated layers. Each layer has one job and a
narrow interface, so parts can be replaced independently.

```
Agent / Developer API          finir.FinancialModel, apply_intent
        │
FinIR Builder                  model.input / define / output
        │
Financial IR                   finir.ir: Module, Expr, types  (.finir / JSON)
        │
Compiler Passes                finir.compiler: validate, typecheck, fold, CSE, DCE, ...
        │
Execution Plan                 needed nodes, dirty cones, backend choice
        │
Incremental Runtime            finir.runtime: engine + cache + state
        │
Kernel Backend                 finir.backends: NumPy (CPU), optional CuPy (GPU)
        │
CPU / SIMD / optional GPU
```

## Responsibilities

| Layer | Module | Job |
|-------|--------|-----|
| API | `finir.model` | ergonomic model building, what-if, scenarios, intent |
| IR | `finir.ir` | typed nodes + expressions; parse/print/serialize/validate |
| Types | `finir.types` | the finance algebra (money/percentage/days/...) |
| Compiler | `finir.compiler` | analysis + optimization passes over the IR |
| Runtime | `finir.runtime` | dependency-aware incremental evaluation + cache + state |
| Backends | `finir.backends` | how a node's arithmetic actually runs, + dispatch |
| Kernels | `finir.kernels` | finance-native operations + the extension registry |
| Stdlib | `finir.stdlib` | reusable model templates |

## Data flow (what happens on `evaluate`)

1. `FinancialModel` validates + type-checks the `Module` and builds an
   `IncrementalEngine` (once; rebuilt only on structural change).
2. The engine computes the set of nodes needed for the requested targets.
3. For each needed node in dependency order: reuse its stored value if still valid
   (O(1)); otherwise recompute via the backend and mark it valid.
4. Changing an input invalidates only its downstream cone, so the next evaluation
   recomputes exactly what changed.

## What FinIR is not

Not a website, dashboard, ERP, FP&A product, trading platform, agent framework, or
generic DAG engine. It is a **compiler/runtime target** for financial computation.
