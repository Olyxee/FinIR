"""The canonical FinIR Intent Contract and its natural-language + execution layers.

    from finir.intent import FinIRIntent, Operation, IntentStatus

    intent = FinIRIntent.from_obj(payload)     # validate a payload
    FinIRIntent.json_schema()                   # the machine-readable contract

The Hugging Face natural-language layer emits the canonical envelope; the runtime
consumes it via :func:`finir.intent.execute_intent` (also reachable through
``FinancialModel.apply_intent``).
"""

from __future__ import annotations

from .compiler import IntentCompiler, MockIntentCompiler
from .execute import IntentExecution, execute_intent
from .schema import (
    SCHEMA_VERSION,
    FinIRIntent,
    IntentStatus,
    IntentValidationError,
    Operation,
    OperationType,
    Scenario,
    load_schema,
)


def json_schema() -> dict:
    """Return the canonical JSON Schema for the FinIR Intent Contract (v1.0)."""
    return load_schema()


__all__ = [
    "SCHEMA_VERSION",
    "FinIRIntent",
    "IntentCompiler",
    "IntentExecution",
    "IntentStatus",
    "IntentValidationError",
    "MockIntentCompiler",
    "Operation",
    "OperationType",
    "Scenario",
    "execute_intent",
    "json_schema",
    "load_schema",
]
