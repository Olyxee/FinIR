"""The incremental execution engine (items 10, 35).

Given a validated, typed :class:`Module`, the engine keeps a persistent value store
and a *validity* set. Changing an input invalidates only its downstream cone
(dirty-set propagation over a precomputed dependents adjacency); the next evaluation
recomputes exactly those nodes and reuses every other value in O(1). Scenario
overrides are evaluated transiently against the persistent base without disturbing
it — so an unaffected node is reused even under a different scenario.

This dirty-propagation design is what makes incremental execution actually cheaper
than full recompute: reuse costs a dict lookup, not a re-derived cache key.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..backends.base import ExecutionBackend
from ..backends.numpy_backend import NumpyBackend
from ..ir.module import Constant, Input, Module
from ..kernels.registry import KernelRegistry, default_registry
from .cache import CacheStats


@dataclass
class RunStats:
    backend: str = "cpu"
    execution_time_s: float = 0.0
    nodes_total: int = 0
    nodes_evaluated: int = 0
    nodes_reused: int = 0
    cache_hit_ratio: float = 0.0
    scenario_size: int = 1
    memory_estimate_bytes: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "execution_time_s": round(self.execution_time_s, 6),
            "nodes_total": self.nodes_total,
            "nodes_evaluated": self.nodes_evaluated,
            "nodes_reused": self.nodes_reused,
            "cache_hit_ratio": round(self.cache_hit_ratio, 4),
            "scenario_size": self.scenario_size,
            "memory_estimate_bytes": self.memory_estimate_bytes,
        }


@dataclass
class EvaluationResult:
    values: dict[str, Any]
    recomputed: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    stats: RunStats = field(default_factory=RunStats)

    def __getitem__(self, name: str) -> Any:
        return self.values[name]

    def __contains__(self, name: str) -> bool:
        return name in self.values

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)


class IncrementalEngine:
    """Executes a module incrementally with dependency-aware invalidation."""

    def __init__(
        self,
        module: Module,
        *,
        kernels: KernelRegistry | None = None,
        backend: ExecutionBackend | None = None,
        model_version: int = 0,
    ) -> None:
        self.module = module
        self.kernels = kernels or default_registry()
        self.backend = backend or NumpyBackend()
        self.model_version = model_version
        self.stats = CacheStats()

        self._topo = module.topo_order()
        self._pos = {n: i for i, n in enumerate(self._topo)}
        self._deps = {n: module.dependencies(n) for n in self._topo}
        self._adj = self._build_adjacency()
        self._needed_cache: dict[tuple[str, ...], list[str]] = {}

        self._input_values: dict[str, Any] = {}
        self._values: dict[str, Any] = {}  # persistent computed values
        self._valid: set[str] = set()  # names whose stored value is current
        for node in module.iter_nodes():
            if isinstance(node, Constant):
                self._values[node.name] = node.value
                self._valid.add(node.name)
            elif isinstance(node, Input) and node.default is not None:
                self.set_input(node.name, node.default)

    # -- inputs --------------------------------------------------------------
    def set_input(self, name: str, value: Any) -> None:
        node = self.module.nodes.get(name)
        if not isinstance(node, Input):
            from ..exceptions import ValidationError

            raise ValidationError(f"{name!r} is not an input")
        self._input_values[name] = value
        # Invalidate this input's downstream cone.
        for d in self._transitive_dependents({name}):
            self._valid.discard(d)

    def input_value(self, name: str) -> Any:
        return self._input_values.get(name)

    def invalidate_all(self) -> None:
        """Force a full recompute on the next evaluation (used by baselines)."""
        self._valid = {n for n in self._topo if isinstance(self.module.nodes[n], Constant)}

    # -- evaluation ----------------------------------------------------------
    def evaluate(
        self,
        targets: list[str] | None = None,
        *,
        overrides: dict[str, Any] | None = None,
        scenario_id: str = "base",
    ) -> EvaluationResult:
        if overrides:
            return self._evaluate_scenario(targets, overrides)
        return self._evaluate_persistent(targets)

    def _evaluate_persistent(self, targets: list[str] | None) -> EvaluationResult:
        start = time.perf_counter()
        needed = self._needed(targets)
        recomputed: list[str] = []
        reused: list[str] = []
        scenario_size = 1
        mem = 0

        for name in needed:  # already topo-ordered
            node = self.module.nodes[name]
            if isinstance(node, Input):
                if name not in self._valid:
                    self._values[name] = self.backend.prepare(self._input_values.get(name, 0.0))
                    self._valid.add(name)
                scenario_size = max(scenario_size, _elements(self._values[name]))
                continue
            if isinstance(node, Constant):
                continue
            if name in self._valid:
                reused.append(name)
                self.stats.hits += 1
                self.stats.reused += 1
            else:
                val = self.backend.eval_expr(node.expr, self._values, self.kernels)
                self._values[name] = val
                self._valid.add(name)
                recomputed.append(name)
                self.stats.misses += 1
                self.stats.recomputed += 1
                mem += _nbytes(val)
            scenario_size = max(scenario_size, _elements(self._values[name]))

        out = self._collect_outputs(targets, self._values)
        stats = self._make_stats(start, recomputed, reused, scenario_size, mem)
        return EvaluationResult(values=out, recomputed=recomputed, reused=reused, stats=stats)

    def _evaluate_scenario(
        self, targets: list[str] | None, overrides: dict[str, Any]
    ) -> EvaluationResult:
        """Transient evaluation of a scenario against the persistent base."""
        start = time.perf_counter()
        needed = self._needed(targets)
        dirty = self._transitive_dependents(set(overrides))
        env: dict[str, Any] = {}
        recomputed: list[str] = []
        reused: list[str] = []
        scenario_size = 1
        mem = 0

        for name in needed:
            node = self.module.nodes[name]
            if isinstance(node, Input):
                if name in overrides:
                    env[name] = self.backend.prepare(overrides[name])
                else:
                    env[name] = self._values.get(
                        name, self.backend.prepare(self._input_values.get(name, 0.0))
                    )
                scenario_size = max(scenario_size, _elements(env[name]))
                continue
            if isinstance(node, Constant):
                env[name] = node.value
                continue
            if name in dirty:
                val = self.backend.eval_expr(node.expr, env, self.kernels)
                env[name] = val
                recomputed.append(name)
                self.stats.misses += 1
                self.stats.recomputed += 1
                mem += _nbytes(val)
            else:
                # Reuse the base value (must have been computed by a base evaluate).
                env[name] = self._values.get(name)
                if env[name] is None:
                    val = self.backend.eval_expr(node.expr, env, self.kernels)
                    env[name] = val
                    recomputed.append(name)
                    self.stats.misses += 1
                    self.stats.recomputed += 1
                else:
                    reused.append(name)
                    self.stats.hits += 1
                    self.stats.reused += 1
            scenario_size = max(scenario_size, _elements(env[name]))

        out = self._collect_outputs(targets, env)
        stats = self._make_stats(start, recomputed, reused, scenario_size, mem)
        return EvaluationResult(values=out, recomputed=recomputed, reused=reused, stats=stats)

    def dirty_nodes(self, changed_inputs: set[str]) -> set[str]:
        """Nodes that would be recomputed if ``changed_inputs`` changed (incl. themselves)."""
        return self._transitive_dependents(changed_inputs)

    # -- internals -----------------------------------------------------------
    def _collect_outputs(self, targets: list[str] | None, store: dict[str, Any]) -> dict[str, Any]:
        names = targets if targets is not None else (self.module.outputs or self._topo)
        return {n: self.backend.finalize(store[n]) for n in names if n in store}

    def _make_stats(self, start, recomputed, reused, scenario_size, mem) -> RunStats:
        return RunStats(
            backend=self.backend.name,
            execution_time_s=time.perf_counter() - start,
            nodes_total=len(self.module.computed()),
            nodes_evaluated=len(recomputed),
            nodes_reused=len(reused),
            cache_hit_ratio=self.stats.hit_ratio,
            scenario_size=scenario_size,
            memory_estimate_bytes=mem,
        )

    def _needed(self, targets: list[str] | None) -> list[str]:
        if targets is None:
            base = tuple(self.module.outputs) or tuple(self._topo)
        else:
            base = tuple(targets)
        if base in self._needed_cache:
            return self._needed_cache[base]
        needed: set[str] = set(base)
        stack = list(base)
        while stack:
            cur = stack.pop()
            for dep in self._deps.get(cur, ()):
                if dep not in needed:
                    needed.add(dep)
                    stack.append(dep)
        ordered = [n for n in self._topo if n in needed]
        self._needed_cache[base] = ordered
        return ordered

    def _transitive_dependents(self, changed: set[str]) -> set[str]:
        seen: set[str] = set()
        stack = list(changed)
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for m in self._adj.get(cur, ()):
                if m not in seen:
                    stack.append(m)
        return seen

    def _build_adjacency(self) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {n: [] for n in self._topo}
        for n in self._topo:
            for dep in self._deps[n]:
                adj.setdefault(dep, []).append(n)
        return adj

    @property
    def cache(self) -> IncrementalEngine:
        # Back-compat shim: expose stats + clear/reset via `.cache` like the old API.
        return self

    def clear(self) -> None:
        self.invalidate_all()

    def reset_stats(self) -> None:
        self.stats = CacheStats()


def _elements(value: Any) -> int:
    if isinstance(value, np.ndarray):
        return int(value.size)
    return 1


def _nbytes(value: Any) -> int:
    if isinstance(value, np.ndarray):
        return int(value.nbytes)
    return 8
