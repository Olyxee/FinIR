"""FinIR kernel library: finance-native operations for the type-checker and runtime."""

from __future__ import annotations

from .registry import (
    Kernel,
    KernelRegistry,
    const_result,
    default_registry,
    first_money_or_scalar,
    kernel,
    same_as_first,
)

__all__ = [
    "Kernel",
    "KernelRegistry",
    "const_result",
    "default_registry",
    "first_money_or_scalar",
    "kernel",
    "same_as_first",
]
