"""Execute a canonical FinIR Intent against a model — the validation boundary.

This is the single point where a canonical intent becomes runtime mutations. It:

1. normalizes any accepted payload to a :class:`FinIRIntent` and structurally validates it;
2. refuses to execute a non-``valid`` intent;
3. semantically validates each operation against the *model's* declared finance types
   (target existence, currency match, unit compatibility) — the type-aware check the
   raw float-setting runtime does not perform at the intent layer;
4. bridges to the runtime: simultaneous operations -> ``what_if``; a ``range`` ->
   ``run_scenarios``; ``scenarios`` -> ``scenarios``.

Grounded entirely in the current runtime API; it adds no new runtime capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from ..types import Days, Percentage, Ratio, Scalar, currency_of, is_money
from .schema import FinIRIntent, IntentStatus, IntentValidationError, Operation, OperationType

if TYPE_CHECKING:
    from ..model import FinancialModel
    from ..runtime.engine import EvaluationResult


@dataclass
class IntentExecution:
    """The result of executing a canonical intent."""

    status: str
    result: EvaluationResult | None = None
    scenario_results: dict[str, EvaluationResult] | None = None


def execute_intent(model: FinancialModel, payload: Any) -> IntentExecution:
    """Validate and execute a canonical intent against ``model``."""
    intent = FinIRIntent.from_obj(payload)  # structural validation happens here

    if intent.status != IntentStatus.VALID:
        raise IntentValidationError(
            f"cannot execute a {intent.status.value} intent"
            + (f": {intent.reason}" if intent.reason else "")
        )
    if not intent.is_executable():
        raise IntentValidationError("valid intent carries no operations or scenarios to execute")

    types = model.types()
    input_names = {i.name for i in model.module.inputs()}

    # Semantic validation against the model's finance types.
    all_ops = list(intent.operations) + [op for s in intent.scenarios for op in s.operations]
    sem_errors: list[str] = []
    for op in all_ops:
        sem_errors.extend(_semantic_errors(op, types, input_names))
    if sem_errors:
        raise IntentValidationError(sem_errors)

    if intent.scenarios:
        spec = {
            s.name: {op.target: op.change_spec() for op in s.operations} for s in intent.scenarios
        }
        return IntentExecution(status="valid", scenario_results=model.scenarios(spec))

    range_ops = [o for o in intent.operations if o.operation == OperationType.RANGE]
    if range_ops:
        o = range_ops[0]
        if o.min is None or o.max is None or o.steps is None:  # guarded by validation
            raise IntentValidationError("range operation requires min, max, and steps")
        grid = np.linspace(o.min, o.max, o.steps)
        return IntentExecution(status="valid", result=model.run_scenarios({o.target: grid}))

    changes = {op.target: op.change_spec() for op in intent.operations}
    return IntentExecution(status="valid", result=model.what_if(changes))


def _semantic_errors(op: Operation, types: dict[str, Any], input_names: set[str]) -> list[str]:
    """Validate one operation against the target's declared finance type."""
    errs: list[str] = []
    if op.target not in input_names:
        errs.append(f"target {op.target!r} is not an input of the model")
        return errs
    ftype = types.get(op.target)
    if ftype is None:
        return errs

    if op.operation == OperationType.RELATIVE_CHANGE:
        # Dimensionless; schema already forbids unit/currency. Nothing type-specific.
        return errs

    if is_money(ftype):
        target_ccy = currency_of(ftype)
        if op.currency is not None and op.currency != target_ccy:
            errs.append(
                f"currency mismatch: target {op.target!r} is money[{target_ccy}] but the "
                f"operation specifies {op.currency} (no implicit FX conversion)"
            )
        if op.unit is not None and op.unit != "money":
            errs.append(f"unit {op.unit!r} is invalid for money target {op.target!r}")
    elif isinstance(ftype, Days):
        if op.currency is not None:
            errs.append(f"currency is invalid for days target {op.target!r}")
        if op.unit is not None and op.unit != "days":
            errs.append(f"unit {op.unit!r} is invalid for days target {op.target!r}")
    elif isinstance(ftype, (Percentage, Ratio, Scalar)):
        if op.currency is not None:
            errs.append(f"currency is invalid for {ftype.textual()} target {op.target!r}")
        if op.unit is not None and op.unit not in ("scalar", "percentage", "ratio"):
            errs.append(f"unit {op.unit!r} is invalid for {ftype.textual()} target {op.target!r}")
    elif op.currency is not None or (op.unit is not None and op.unit != "scalar"):
        errs.append(f"unit/currency not applicable to {ftype.textual()} target {op.target!r}")

    return errs
