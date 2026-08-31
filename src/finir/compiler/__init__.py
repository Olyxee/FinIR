"""FinIR compiler: passes over the IR producing an optimized, typed module."""

from __future__ import annotations

from .passes import (
    DEFAULT_PIPELINE,
    CompiledModule,
    CompileReport,
    compile_module,
)

__all__ = [
    "DEFAULT_PIPELINE",
    "CompileReport",
    "CompiledModule",
    "compile_module",
]
