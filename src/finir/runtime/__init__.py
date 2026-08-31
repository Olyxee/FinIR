"""FinIR incremental runtime: engine, cache, state, scenarios."""

from __future__ import annotations

from .cache import CacheStats, ComputationCache
from .engine import EvaluationResult, IncrementalEngine, RunStats
from .scenario import resolve_change
from .state import ModelState

__all__ = [
    "CacheStats",
    "ComputationCache",
    "EvaluationResult",
    "IncrementalEngine",
    "ModelState",
    "RunStats",
    "resolve_change",
]
