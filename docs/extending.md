# Extending FinIR

FinIR is small on purpose; you extend it at clean seams.

## Custom kernels

```python
from finir import kernel
from finir.types import Money


@kernel("logistics.landed_cost", result=Money("ZAR"), arity=2)
def landed_cost(unit_cost, freight):
    return unit_cost + freight
```

`result` is a fixed `FinType` or a rule `list[FinType] -> FinType`. The kernel is now
available in any expression and to the type-checker. Numeric implementations should
work on scalars **and** NumPy arrays (write them with NumPy).

## Custom templates (stdlib)

A template is just a function that adds nodes to a model:

```python
def my_operating_model(model):
    model.define("contribution", "revenue - variable_cost")
    model.define("contribution_margin", "contribution / revenue")
    return model
```

## Custom backends

Implement `ExecutionBackend` — a `binary(op, a, b)` and (optionally) `prepare` /
`finalize` for device marshalling. The default `eval_expr` walks the AST for you;
override `call_kernel` if kernels need special handling on your device.

```python
from finir.backends.base import ExecutionBackend


class MyBackend(ExecutionBackend):
    name = "mybackend"

    def binary(self, op, a, b):
        return self._apply(op, a, b)


model.set_backend(MyBackend())
```

## Language bindings

The IR's JSON form (`module_to_json` / `module_from_json`) is the stable, neutral
interchange format. Other languages (TypeScript, Rust, Java, ...) can consume a
FinIR module by reading that JSON — no Python required. The Python package is the
reference implementation; additional SDKs are future work, not shipped now.

## Numeric policy

`finir.numerics.set_policy(NumericPolicy(on_div_zero="raise"))` controls
division-by-zero and non-finite handling; a Decimal path is available for
money-sensitive scalar math (`to_decimal`). Vectorized workloads use float64 — a
documented precision trade-off.
