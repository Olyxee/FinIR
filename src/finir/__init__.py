"""FinIR — a financial intermediate representation and incremental execution runtime.

    from finir import FinancialModel

    model = FinancialModel()
    model.input("revenue", 500_000_000, currency="ZAR")
    model.input("cogs", 300_000_000, currency="ZAR")
    model.define("gross_profit", "revenue - cogs")
    model.evaluate()["gross_profit"]

FinIR gives AI-generated financial computation a dedicated compiler target: a typed
IR, dependency-aware incremental execution, a finance-native cache, a scenario
engine, and workload-aware CPU/GPU dispatch.
"""

from __future__ import annotations

from .exceptions import (
    BackendError,
    CurrencyError,
    FinIRError,
    KernelError,
    NumericError,
    ParseError,
    TypeCheckError,
    ValidationError,
)
from .intent import IntentCompiler, MockIntentCompiler
from .kernels.registry import kernel
from .model import FinancialModel
from .version import __version__

# Lazily re-exported to keep import time low; see __getattr__.
__all__ = [
    "BackendError",
    "CurrencyError",
    "FinIRError",
    "FinancialModel",
    "IntentCompiler",
    "KernelError",
    "MockIntentCompiler",
    "NumericError",
    "ParseError",
    "TypeCheckError",
    "ValidationError",
    "__version__",
    "compile_model",
    "kernel",
    "parse",
]


def parse(text: str, *, name: str = "model"):
    """Parse a ``.finir`` textual module into an IR :class:`~finir.ir.module.Module`."""
    from .ir.parser import parse_module

    return parse_module(text, name=name)


def compile_model(module, **kwargs):
    """Run the compiler pipeline over an IR module; returns a CompiledModule."""
    from .compiler import compile_module

    return compile_module(module, **kwargs)
