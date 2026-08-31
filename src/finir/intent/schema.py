"""Canonical FinIR Intent Contract — Python types (schema version 1.0).

These types map 1:1 to ``schemas/finir-intent-v1.schema.json`` (a byte-identical
copy is packaged here as ``finir-intent-v1.schema.json``). They are the single
source of truth on the runtime side; the Hugging Face natural-language layer emits
objects that validate against the same schema.

The project uses dataclasses (no Pydantic dependency). ``FinIRIntent`` provides the
pydantic-equivalent surface Alisha needs: :meth:`FinIRIntent.from_obj` (validate a
payload), :meth:`FinIRIntent.to_dict` (serialize), and :meth:`FinIRIntent.json_schema`
(the machine-readable contract).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from importlib import resources
from typing import Any

from ..exceptions import FinIRError

SCHEMA_VERSION = "1.0"
_SCHEMA_FILE = "finir-intent-v1.schema.json"


class IntentValidationError(FinIRError):
    """A payload did not satisfy the canonical FinIR Intent Contract."""

    code = "intent_validation_error"

    def __init__(self, errors: list[str] | str) -> None:
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))


class IntentStatus(StrEnum):
    """The four contract states."""

    VALID = "valid"  # safe to execute
    AMBIGUOUS = "ambiguous"  # understandable but missing required quantitative detail
    UNSUPPORTED = "unsupported"  # clear but FinIR cannot represent it
    INVALID = "invalid"  # structurally or semantically invalid


class OperationType(StrEnum):
    """The executable operation kinds the runtime supports."""

    RELATIVE_CHANGE = "relative_change"  # new = current * (1 + value)
    SET = "set"  # new = value
    ABSOLUTE_CHANGE = "absolute_change"  # new = current + value
    RANGE = "range"  # batch sweep of `steps` values over [min, max]


# Legacy operation aliases accepted for backward compatibility (normalized on load).
_OP_ALIASES = {"change": "relative_change", "delta": "absolute_change"}

_ALLOWED_UNITS = {"money", "percentage", "ratio", "days", "rate", "quantity", "scalar"}


@dataclass
class Operation:
    """One structured operation against a model input node."""

    operation: OperationType
    target: str
    value: float | None = None
    unit: str | None = None
    currency: str | None = None
    min: float | None = None
    max: float | None = None
    steps: int | None = None

    # -- construction --------------------------------------------------------
    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> Operation:
        if not isinstance(obj, dict):
            raise IntentValidationError("operation must be an object")
        raw_op = str(obj.get("operation", "relative_change"))
        op_name = _OP_ALIASES.get(raw_op, raw_op)
        if op_name not in {o.value for o in OperationType}:
            raise IntentValidationError(f"unknown operation {op_name!r}")
        target = obj.get("target") or obj.get("metric")
        if not isinstance(target, str) or not target:
            raise IntentValidationError("operation is missing a target")
        # Legacy: relative change carried under a 'relative_change' value key.
        value = obj.get("value", obj.get("relative_change"))
        return cls(
            operation=OperationType(op_name),
            target=target,
            value=None if value is None else float(value),
            unit=obj.get("unit"),
            currency=obj.get("currency"),
            min=None if obj.get("min") is None else float(obj["min"]),
            max=None if obj.get("max") is None else float(obj["max"]),
            steps=None if obj.get("steps") is None else int(obj["steps"]),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"operation": self.operation.value, "target": self.target}
        for key in ("value", "unit", "currency", "min", "max", "steps"):
            v = getattr(self, key)
            if v is not None:
                out[key] = v
        return out

    # -- runtime bridge ------------------------------------------------------
    def change_spec(self) -> dict[str, float]:
        """The runtime change spec (finir.runtime.scenario.resolve_change) for this op."""
        if self.operation == OperationType.RELATIVE_CHANGE:
            return {"relative": float(self.value or 0.0)}
        if self.operation == OperationType.SET:
            return {"absolute": float(self.value or 0.0)}
        if self.operation == OperationType.ABSOLUTE_CHANGE:
            return {"delta": float(self.value or 0.0)}
        raise IntentValidationError(f"operation {self.operation.value!r} is not a scalar change")

    # -- validation ----------------------------------------------------------
    def structural_errors(self) -> list[str]:
        errs: list[str] = []
        if not self.target:
            errs.append("operation is missing a target")
        if self.unit is not None and self.unit not in _ALLOWED_UNITS:
            errs.append(f"unknown unit {self.unit!r}")
        if self.currency is not None and not (len(self.currency) == 3 and self.currency.isupper()):
            errs.append(f"currency {self.currency!r} must be a 3-letter ISO-4217 code")
        if self.operation == OperationType.RANGE:
            if self.value is not None:
                errs.append("range operation must not carry 'value'")
            for f in ("min", "max", "steps"):
                if getattr(self, f) is None:
                    errs.append(f"range operation requires '{f}'")
            if self.steps is not None and self.steps < 2:
                errs.append("range 'steps' must be >= 2")
        else:
            if self.value is None:
                errs.append(f"{self.operation.value} operation requires 'value'")
            for f in ("min", "max", "steps"):
                if getattr(self, f) is not None:
                    errs.append(f"{self.operation.value} operation must not carry '{f}'")
            if self.operation == OperationType.RELATIVE_CHANGE and (
                self.unit is not None or self.currency is not None
            ):
                errs.append("relative_change is dimensionless: it must not carry unit/currency")
        return errs


@dataclass
class Scenario:
    """A named scenario: simultaneous operations against the base state."""

    name: str
    operations: list[Operation] = field(default_factory=list)

    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> Scenario:
        return cls(
            name=obj.get("name", ""),
            operations=[Operation.from_obj(o) for o in obj.get("operations", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "operations": [o.to_dict() for o in self.operations]}


@dataclass
class FinIRIntent:
    """The top-level canonical intent envelope (schema version 1.0)."""

    schema_version: str = SCHEMA_VERSION
    status: IntentStatus = IntentStatus.VALID
    reason: str | None = None
    operations: list[Operation] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)

    # -- construction --------------------------------------------------------
    @classmethod
    def from_obj(cls, payload: Any) -> FinIRIntent:
        """Normalize any accepted payload into a validated FinIRIntent.

        Accepts: a FinIRIntent (returned as-is), the canonical envelope dict, or a
        legacy single-operation dict (``{"operation": ..., "target": ..., "value": ...}``).
        """
        if isinstance(payload, FinIRIntent):
            return payload
        if not isinstance(payload, dict):
            raise IntentValidationError("intent payload must be an object")

        # Legacy single-operation dict -> wrap in a valid envelope.
        if "operations" not in payload and "scenarios" not in payload and "operation" in payload:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "status": "valid",
                "operations": [payload],
            }

        status_raw = payload.get("status", "valid")
        try:
            status = IntentStatus(status_raw)
        except ValueError as exc:
            raise IntentValidationError(f"unknown status {status_raw!r}") from exc

        intent = cls(
            schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
            status=status,
            reason=payload.get("reason"),
            operations=[Operation.from_obj(o) for o in payload.get("operations", [])],
            scenarios=[Scenario.from_obj(s) for s in payload.get("scenarios", [])],
        )
        errs = intent.structural_errors()
        if errs:
            raise IntentValidationError(errs)
        return intent

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"schema_version": self.schema_version, "status": self.status.value}
        if self.reason is not None:
            out["reason"] = self.reason
        if self.scenarios:
            out["scenarios"] = [s.to_dict() for s in self.scenarios]
        else:
            out["operations"] = [o.to_dict() for o in self.operations]
        return out

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    # -- queries -------------------------------------------------------------
    def is_executable(self) -> bool:
        return self.status == IntentStatus.VALID and bool(self.operations or self.scenarios)

    # -- validation ----------------------------------------------------------
    def structural_errors(self) -> list[str]:
        """Structural (model-free) validation mirroring the JSON Schema."""
        errs: list[str] = []
        if self.schema_version != SCHEMA_VERSION:
            errs.append(
                f"unsupported schema_version {self.schema_version!r} (expected {SCHEMA_VERSION})"
            )
        if self.status != IntentStatus.VALID and (self.operations or self.scenarios):
            errs.append(f"a {self.status.value} intent must carry no operations or scenarios")
        if self.operations and self.scenarios:
            errs.append("an intent carries either operations or scenarios, not both")
        for op in self.operations:
            errs.extend(op.structural_errors())
        # Duplicate targets across simultaneous operations are ambiguous -> invalid.
        targets = [o.target for o in self.operations]
        dupes = sorted({t for t in targets if targets.count(t) > 1})
        if dupes:
            errs.append(f"duplicate target(s) in simultaneous operations: {dupes}")
        # A range operation must be the sole operation (it is a vectorized batch).
        if (
            any(o.operation == OperationType.RANGE for o in self.operations)
            and len(self.operations) > 1
        ):
            errs.append("a range operation must be the only operation in the intent")
        for sc in self.scenarios:
            if not sc.name:
                errs.append("scenario is missing a name")
            for op in sc.operations:
                if op.operation == OperationType.RANGE:
                    errs.append("scenarios may not contain range operations")
                errs.extend(op.structural_errors())
        return errs

    # -- contract artifact ---------------------------------------------------
    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        """Return the canonical JSON Schema (the machine-readable contract)."""
        return load_schema()


def load_schema() -> dict[str, Any]:
    """Load the packaged canonical JSON Schema for the intent contract."""
    text = resources.files("finir.intent").joinpath(_SCHEMA_FILE).read_text(encoding="utf-8")
    return json.loads(text)
