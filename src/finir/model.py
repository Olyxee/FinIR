"""The high-level :class:`FinancialModel` API (items 8, 9, 12, 21, 33).

This is the ergonomic front door. It owns a FinIR :class:`Module`, a validated/typed
:class:`IncrementalEngine` (which keeps the computation cache warm across calls), a
backend planner, and the scenario/what-if helpers. Structural changes rebuild the
engine; value changes and scenarios reuse the cache incrementally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .backends.base import ExecutionBackend
from .backends.dispatch import BackendPlanner, WorkloadProfile
from .ir.module import Constant, Input, Module
from .ir.parser import parse_expr
from .ir.serialize import module_from_json, module_to_json
from .ir.typeinfer import infer_module_types
from .ir.validate import validate_module
from .kernels.registry import KernelRegistry, default_registry
from .runtime.engine import EvaluationResult, IncrementalEngine
from .runtime.scenario import resolve_change
from .runtime.state import ModelState
from .types import FinType, Money, Scalar, parse_type


class FinancialModel:
    """A finance-native computation model with incremental execution."""

    def __init__(self, name: str = "model", *, kernels: KernelRegistry | None = None) -> None:
        self.module = Module(name=name)
        self.kernels = kernels or default_registry()
        self.planner = BackendPlanner()
        self._engine: IncrementalEngine | None = None
        self._pending_values: dict[str, Any] = {}
        self._structure_version = 0
        self._base_evaluated = False

    # -- construction --------------------------------------------------------
    def input(
        self,
        name: str,
        value: Any = None,
        *,
        currency: str | None = None,
        type: FinType | str | None = None,
    ) -> FinancialModel:
        """Declare a model input. ``currency`` is shorthand for ``money[CCY]``."""
        ftype = self._resolve_type(type, currency)
        default = float(value) if isinstance(value, (int, float)) else None
        self.module.add(Input(name, ftype, default))
        if value is not None:
            self._pending_values[name] = value
        self._invalidate()
        return self

    def input_series(
        self, name: str, values: list[float], *, period: str = "month", currency: str | None = None
    ) -> FinancialModel:
        """Declare a time-series input (item 28)."""
        from .types import Series

        element = self._resolve_type(None, currency)
        self.module.add(Input(name, Series(element, period)))
        self._pending_values[name] = np.asarray(values, dtype="float64")
        self._invalidate()
        return self

    def constant(
        self, name: str, value: float, *, type: FinType | str | None = None
    ) -> FinancialModel:
        self.module.add(Constant(name, float(value), self._resolve_type(type, None)))
        self._invalidate()
        return self

    def define(self, name: str, expr: str, *, output: bool = False) -> FinancialModel:
        from .ir.module import Computed

        self.module.add(Computed(name, parse_expr(expr)))
        if output:
            self.module.set_output(name)
        self._invalidate()
        return self

    def output(self, *names: str) -> FinancialModel:
        for n in names:
            self.module.set_output(n)
        return self

    # -- values --------------------------------------------------------------
    def set(self, name: str, value: Any) -> FinancialModel:
        """Change an input value (dirties only its downstream cone)."""
        self._ensure_engine().set_input(name, value)
        self._base_evaluated = False
        return self

    # -- evaluation ----------------------------------------------------------
    def evaluate(
        self,
        targets: list[str] | None = None,
        *,
        backend: str | None = None,
    ) -> EvaluationResult:
        engine = self._ensure_engine()
        if backend is not None:
            engine.backend = self.planner.get(backend)
        result = engine.evaluate(targets)
        self._base_evaluated = True
        return result

    def what_if(
        self,
        changes: dict[str, Any] | None = None,
        *,
        targets: list[str] | None = None,
        **kw_changes: Any,
    ) -> EvaluationResult:
        """Evaluate a scenario given per-input change specs; unaffected nodes are reused.

        Change specs may be passed positionally as a dict or as keyword arguments::

            model.what_if(cogs="+4%")
            model.what_if({"cogs": {"relative": 0.04}})
        """
        engine = self._ensure_engine()
        self._ensure_base()
        merged = {**(changes or {}), **kw_changes}
        overrides = {
            name: resolve_change(engine.input_value(name), spec) for name, spec in merged.items()
        }
        return engine.evaluate(targets, overrides=overrides, scenario_id="what_if")

    def scenarios(self, spec: dict[str, dict[str, Any]]) -> dict[str, EvaluationResult]:
        """Run named scenarios (item 12); each reuses the base cache incrementally."""
        engine = self._ensure_engine()
        self._ensure_base()
        out: dict[str, EvaluationResult] = {}
        for label, changes in spec.items():
            overrides = {
                name: resolve_change(engine.input_value(name), s) for name, s in changes.items()
            }
            out[label] = engine.evaluate(overrides=overrides, scenario_id=label)
        return out

    def run_scenarios(
        self, *, targets: list[str] | None = None, backend: str | None = None, **arrays: Any
    ) -> EvaluationResult:
        """Run a large batch of scenarios by setting inputs to arrays (vectorized)."""
        engine = self._ensure_engine()
        overrides = {name: np.asarray(v, dtype="float64") for name, v in arrays.items()}
        size = max((v.size for v in overrides.values()), default=1)
        if backend is not None:
            engine.backend = self.planner.get(backend)
        else:
            choice = self.planner.choose(
                WorkloadProfile(scenario_size=size, node_count=len(self.module.computed()))
            )
            engine.backend = choice.backend
        # A batch changes the cache key space; evaluate fresh (no false reuse).
        return engine.evaluate(targets, overrides=overrides, scenario_id=f"batch_{size}")

    # -- agent API -----------------------------------------------------------
    def apply_intent(self, intent: dict[str, Any]) -> EvaluationResult:
        """Execute a structured financial intent (item 9).

        Shapes accepted::

            {"operation": "relative_change", "target": "cogs", "value": 0.04}
            {"operation": "set", "target": "revenue", "value": 5.2e8}
            {"operation": "change", "metric": "cogs", "relative_change": 0.04}
        """
        op = intent.get("operation", "relative_change")
        target = intent.get("target") or intent.get("metric")
        if target is None:
            from .exceptions import FinIRError

            raise FinIRError("intent must name a target/metric")
        if op in ("relative_change", "change") and (
            "value" in intent or "relative_change" in intent
        ):
            rel = intent.get("relative_change", intent.get("value"))
            if rel is None:
                from .exceptions import FinIRError

                raise FinIRError("relative_change intent requires a value")
            return self.what_if({target: {"relative": float(rel)}})
        if op == "set":
            return self.what_if({target: {"absolute": float(intent["value"])}})
        if op == "delta":
            return self.what_if({target: {"delta": float(intent["value"])}})
        from .exceptions import FinIRError

        raise FinIRError(f"unknown intent operation {op!r}")

    # -- state snapshots -----------------------------------------------------
    def state(self) -> ModelState:
        engine = self._ensure_engine()
        return ModelState(values={i.name: engine.input_value(i.name) for i in self.module.inputs()})

    def evaluate_state(
        self, state: ModelState, targets: list[str] | None = None
    ) -> EvaluationResult:
        engine = self._ensure_engine()
        self._ensure_base()
        return engine.evaluate(targets, overrides=dict(state.values), scenario_id="state")

    # -- introspection -------------------------------------------------------
    def cache_stats(self) -> dict[str, Any]:
        return self._ensure_engine().cache.stats.as_dict()

    def types(self) -> dict[str, FinType]:
        return infer_module_types(self.module, kernel=self.kernels.result_type)

    def dirty_nodes(self, *changed: str) -> list[str]:
        return sorted(self._ensure_engine().dirty_nodes(set(changed)))

    # -- persistence ---------------------------------------------------------
    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self._to_json(), indent=2), encoding="utf-8")

    @classmethod
    def from_ir(cls, module: Module, *, kernels: KernelRegistry | None = None) -> FinancialModel:
        """Wrap an existing IR module (e.g. parsed from ``.finir``) in a model."""
        model = cls(name=module.name, kernels=kernels)
        model.module = module
        for node in module.iter_nodes():
            if isinstance(node, Input) and node.default is not None:
                model._pending_values[node.name] = node.default
        model._invalidate()
        return model

    @classmethod
    def load(cls, path: str | Path) -> FinancialModel:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls(name=obj["module"]["name"])
        model.module = module_from_json(obj["module"])
        model._pending_values = {
            k: (np.asarray(v, dtype="float64") if isinstance(v, list) else v)
            for k, v in obj.get("values", {}).items()
        }
        model._invalidate()
        return model

    def _to_json(self) -> dict[str, Any]:
        vals: dict[str, Any] = {}
        engine = self._engine
        for i in self.module.inputs():
            v = engine.input_value(i.name) if engine else self._pending_values.get(i.name)
            if isinstance(v, np.ndarray):
                v = v.tolist()
            if v is not None:
                vals[i.name] = v
        return {"module": module_to_json(self.module), "values": vals}

    # -- internals -----------------------------------------------------------
    def _resolve_type(self, type: FinType | str | None, currency: str | None) -> FinType:
        if type is not None:
            return type if isinstance(type, FinType) else parse_type(type)
        if currency is not None:
            return Money(currency)
        return Scalar()

    def _invalidate(self) -> None:
        self._structure_version += 1
        self._engine = None
        self._base_evaluated = False

    def _ensure_engine(self) -> IncrementalEngine:
        if self._engine is None:
            validate_module(self.module)
            infer_module_types(self.module, kernel=self.kernels.result_type)
            engine = IncrementalEngine(
                self.module, kernels=self.kernels, model_version=self._structure_version
            )
            for name, value in self._pending_values.items():
                engine.set_input(name, value)
            self._engine = engine
        return self._engine

    def _ensure_base(self) -> None:
        if not self._base_evaluated:
            self._ensure_engine().evaluate()
            self._base_evaluated = True

    def set_backend(self, backend: ExecutionBackend) -> None:
        self._ensure_engine().backend = backend
