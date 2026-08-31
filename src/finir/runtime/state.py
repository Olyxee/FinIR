"""Versioned model state snapshots (item 21).

A :class:`ModelState` is an immutable snapshot of the inputs plus the set of inputs
that changed relative to the state it was derived from. Chaining ``with_change``
gives an AI agent a clean, inspectable trail of iterative reasoning, and lets the
engine recompute only what each step dirtied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .scenario import resolve_change


@dataclass(frozen=True)
class ModelState:
    """An immutable snapshot of input values."""

    values: dict[str, Any] = field(default_factory=dict)
    changed: tuple[str, ...] = ()

    def with_change(
        self,
        name: str,
        *,
        relative: float | None = None,
        absolute: float | None = None,
        delta: float | None = None,
        spec: Any = None,
    ) -> ModelState:
        """Return a new state with one input changed."""
        current = self.values.get(name)
        if spec is not None:
            new_value = resolve_change(current, spec)
        elif relative is not None:
            new_value = resolve_change(current, {"relative": relative})
        elif absolute is not None:
            new_value = float(absolute)
        elif delta is not None:
            new_value = resolve_change(current, {"delta": delta})
        else:
            raise ValueError("with_change requires one of spec/relative/absolute/delta")
        new_values = dict(self.values)
        new_values[name] = new_value
        return ModelState(values=new_values, changed=(name,))

    def with_changes(self, changes: dict[str, Any]) -> ModelState:
        new_values = dict(self.values)
        changed = []
        for name, spec in changes.items():
            new_values[name] = resolve_change(self.values.get(name), spec)
            changed.append(name)
        return ModelState(values=new_values, changed=tuple(changed))
