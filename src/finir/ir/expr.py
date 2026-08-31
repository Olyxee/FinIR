"""Expression AST for FinIR computed nodes.

A computed node is defined by a small expression tree over references to other
nodes, numeric literals, binary arithmetic, and kernel calls. The tree is the unit
the compiler analyses (dependencies, constant folding, CSE, fusion) and the runtime
evaluates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import FinType, Percentage, Scalar


@dataclass(frozen=True)
class Expr:
    """Base class for expression nodes."""


@dataclass(frozen=True)
class Ref(Expr):
    """Reference to another named node."""

    name: str


@dataclass(frozen=True)
class Lit(Expr):
    """A numeric literal with a finance type (scalar by default, or percentage)."""

    value: float
    type: FinType = field(default_factory=Scalar)


@dataclass(frozen=True)
class Bin(Expr):
    """A binary arithmetic operation: + - * /."""

    op: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Call(Expr):
    """A kernel call, e.g. ``npv(rate, cashflows)``."""

    func: str
    args: tuple[Expr, ...]


def free_refs(expr: Expr) -> set[str]:
    """All node names referenced anywhere in the expression."""
    if isinstance(expr, Ref):
        return {expr.name}
    if isinstance(expr, Bin):
        return free_refs(expr.left) | free_refs(expr.right)
    if isinstance(expr, Call):
        out: set[str] = set()
        for a in expr.args:
            out |= free_refs(a)
        return out
    return set()


_PREC = {"+": 1, "-": 1, "*": 2, "/": 2}


def expr_to_text(expr: Expr, parent_prec: int = 0) -> str:
    """Render an expression back to readable infix text."""
    if isinstance(expr, Ref):
        return expr.name
    if isinstance(expr, Lit):
        if isinstance(expr.type, Percentage):
            return f"{expr.value * 100:g}%"
        return f"{expr.value:g}"
    if isinstance(expr, Bin):
        prec = _PREC[expr.op]
        s = f"{expr_to_text(expr.left, prec)} {expr.op} {expr_to_text(expr.right, prec + 1)}"
        return f"({s})" if prec < parent_prec else s
    if isinstance(expr, Call):
        inner = ", ".join(expr_to_text(a) for a in expr.args)
        return f"{expr.func}({inner})"
    raise TypeError(f"unknown expr {expr!r}")


def structural_key(expr: Expr) -> str:
    """A canonical string identifying the expression's shape (for CSE)."""
    if isinstance(expr, Ref):
        return f"ref:{expr.name}"
    if isinstance(expr, Lit):
        return f"lit:{expr.value}:{expr.type.textual()}"
    if isinstance(expr, Bin):
        return f"({structural_key(expr.left)}{expr.op}{structural_key(expr.right)})"
    if isinstance(expr, Call):
        return f"{expr.func}({','.join(structural_key(a) for a in expr.args)})"
    raise TypeError(f"unknown expr {expr!r}")
