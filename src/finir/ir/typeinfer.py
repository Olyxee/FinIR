"""Type inference over a FinIR module.

Walks the module in dependency order, giving every computed node a concrete
:class:`FinType` from the finance-aware algebra in :mod:`finir.types`. Invalid
operations (mixing currencies, adding money to days) raise here — this is where the
type system protects agent-generated computations.
"""

from __future__ import annotations

from collections.abc import Callable

from ..types import FinType, binary_result
from .expr import Bin, Call, Expr, Lit, Ref
from .module import Computed, Module

# A resolver mapping (kernel name, arg types) -> result type.
KernelResolver = Callable[[str, list[FinType]], FinType]


def _default_kernel_resolver(name: str, arg_types: list[FinType]) -> FinType:
    from ..kernels.registry import default_registry

    return default_registry().result_type(name, arg_types)


def infer_expr_type(expr: Expr, env: dict[str, FinType], kernel: KernelResolver) -> FinType:
    if isinstance(expr, Ref):
        if expr.name not in env:
            from ..exceptions import ValidationError

            raise ValidationError(f"reference to unknown or not-yet-defined node {expr.name!r}")
        return env[expr.name]
    if isinstance(expr, Lit):
        return expr.type
    if isinstance(expr, Bin):
        return binary_result(
            expr.op,
            infer_expr_type(expr.left, env, kernel),
            infer_expr_type(expr.right, env, kernel),
        )
    if isinstance(expr, Call):
        return kernel(expr.func, [infer_expr_type(a, env, kernel) for a in expr.args])
    raise TypeError(f"unknown expr {expr!r}")


def infer_module_types(
    module: Module, *, kernel: KernelResolver | None = None
) -> dict[str, FinType]:
    """Infer and assign types for all nodes; returns name -> type."""
    resolver = kernel or _default_kernel_resolver
    env: dict[str, FinType] = {}
    for name in module.topo_order():
        node = module.nodes[name]
        if isinstance(node, Computed):
            t = infer_expr_type(node.expr, env, resolver)
            node.type = t
            env[name] = t
        else:
            env[name] = node.type
    return env
