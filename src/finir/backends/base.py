"""Execution backend interface.

A backend evaluates FinIR expressions over concrete values. The engine owns the
graph, caching, and scheduling; the backend owns *how* a single node's arithmetic
runs (scalar, vectorized CPU, or GPU). Keeping this boundary clean is what lets the
same computation graph dispatch to different hardware.
"""

from __future__ import annotations

import abc
from typing import Any

from ..ir.expr import Bin, Call, Expr, Lit, Ref
from ..kernels.registry import KernelRegistry
from ..numerics import safe_div


class ExecutionBackend(abc.ABC):
    """Evaluate expressions over values of some numeric representation."""

    name: str = "base"

    @property
    def available(self) -> bool:
        return True

    # Input/output marshalling (identity for CPU; device transfer for GPU).
    def prepare(self, value: Any) -> Any:
        return value

    def finalize(self, value: Any) -> Any:
        return value

    @abc.abstractmethod
    def binary(self, op: str, a: Any, b: Any) -> Any: ...

    def eval_expr(self, expr: Expr, env: dict[str, Any], kernels: KernelRegistry) -> Any:
        if isinstance(expr, Ref):
            return env[expr.name]
        if isinstance(expr, Lit):
            return expr.value
        if isinstance(expr, Bin):
            return self.binary(
                expr.op,
                self.eval_expr(expr.left, env, kernels),
                self.eval_expr(expr.right, env, kernels),
            )
        if isinstance(expr, Call):
            args = [self.eval_expr(a, env, kernels) for a in expr.args]
            return self.call_kernel(kernels, expr.func, args)
        raise TypeError(f"unknown expr {expr!r}")

    def call_kernel(self, kernels: KernelRegistry, name: str, args: list[Any]) -> Any:
        return kernels.call(name, args)

    @staticmethod
    def _apply(op: str, a: Any, b: Any) -> Any:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return safe_div(a, b)
        raise ValueError(f"unknown operator {op!r}")
