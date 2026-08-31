"""The FinIR kernel registry.

A *kernel* is a named, finance-native operation with (a) a numeric implementation
that works on scalars and NumPy arrays alike, and (b) a type rule for the
type-checker. Arithmetic ``+ - * /`` are core IR operators; kernels cover the named
financial primitives (margins, working capital, TVM, risk) and user extensions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..exceptions import KernelError
from ..types import FinType, Money, Ratio, Scalar

ResultRule = Callable[[list[FinType]], FinType]


@dataclass
class Kernel:
    name: str
    fn: Callable[..., Any]
    result: ResultRule
    arity: int | None = None  # None => variadic
    doc: str = ""


# -- result-type helpers -----------------------------------------------------
def first_money_or_scalar(arg_types: list[FinType]) -> FinType:
    for t in arg_types:
        if isinstance(t, Money):
            return t
    return Scalar()


def const_result(t: FinType) -> ResultRule:
    return lambda _at: t


def same_as_first(arg_types: list[FinType]) -> FinType:
    return arg_types[0] if arg_types else Scalar()


class KernelRegistry:
    def __init__(self) -> None:
        self._kernels: dict[str, Kernel] = {}

    def register(self, kernel: Kernel, *, overwrite: bool = False) -> Kernel:
        if kernel.name in self._kernels and not overwrite:
            raise KernelError(f"kernel {kernel.name!r} is already registered")
        self._kernels[kernel.name] = kernel
        return kernel

    def add(
        self,
        name: str,
        fn: Callable[..., Any],
        result: ResultRule,
        *,
        arity: int | None = None,
        doc: str = "",
        overwrite: bool = False,
    ) -> Kernel:
        return self.register(
            Kernel(name=name, fn=fn, result=result, arity=arity, doc=doc), overwrite=overwrite
        )

    def has(self, name: str) -> bool:
        return name in self._kernels

    def get(self, name: str) -> Kernel:
        if name not in self._kernels:
            raise KernelError(f"unknown kernel {name!r}")
        return self._kernels[name]

    def names(self) -> list[str]:
        return sorted(self._kernels)

    def result_type(self, name: str, arg_types: list[FinType]) -> FinType:
        kernel = self.get(name)
        if kernel.arity is not None and len(arg_types) != kernel.arity:
            raise KernelError(f"kernel {name!r} expects {kernel.arity} args, got {len(arg_types)}")
        return kernel.result(arg_types)

    def call(self, name: str, values: list[Any]) -> Any:
        kernel = self.get(name)
        if kernel.arity is not None and len(values) != kernel.arity:
            raise KernelError(f"kernel {name!r} expects {kernel.arity} args, got {len(values)}")
        return kernel.fn(*values)


_DEFAULT: KernelRegistry | None = None


def default_registry() -> KernelRegistry:
    """The process-wide registry with all built-in kernels loaded."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = KernelRegistry()
        from . import arithmetic, corporate, risk, tvm, working_capital

        for mod in (arithmetic, corporate, working_capital, tvm, risk):
            mod.register_all(_DEFAULT)
    return _DEFAULT


def kernel(
    name: str,
    *,
    result: ResultRule | FinType = Scalar(),
    arity: int | None = None,
    doc: str = "",
    registry: KernelRegistry | None = None,
):
    """Decorator to register a custom kernel (item 31).

    ``result`` may be a fixed :class:`FinType` or a rule ``list[FinType] -> FinType``.
    """
    rule: ResultRule = result if callable(result) else const_result(result)

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        reg = registry or default_registry()
        reg.add(name, fn, rule, arity=arity, doc=doc or (fn.__doc__ or ""), overwrite=True)
        return fn

    return deco


# Common re-exports for kernel modules.
__all__ = [
    "Kernel",
    "KernelRegistry",
    "Ratio",
    "const_result",
    "default_registry",
    "first_money_or_scalar",
    "kernel",
    "same_as_first",
]
