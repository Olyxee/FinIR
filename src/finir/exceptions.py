"""FinIR exception hierarchy.

Every error raised deliberately by the framework derives from :class:`FinIRError`
so callers can catch the whole family, and each carries a stable ``code`` for
programmatic handling and CLI reporting.
"""

from __future__ import annotations


class FinIRError(Exception):
    """Base class for all FinIR errors."""

    code: str = "finir_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ParseError(FinIRError):
    """The textual IR / expression could not be parsed."""

    code = "parse_error"


class TypeCheckError(FinIRError):
    """An operation is invalid under the finance-aware type system."""

    code = "type_error"


class CurrencyError(TypeCheckError):
    """Two different currencies were combined without an explicit conversion."""

    code = "currency_error"


class ValidationError(FinIRError):
    """The IR module is structurally invalid (cycle, unknown reference, ...)."""

    code = "validation_error"


class KernelError(FinIRError):
    """A kernel is unknown, or was given the wrong arity/types."""

    code = "kernel_error"


class BackendError(FinIRError):
    """An execution backend is unavailable or failed."""

    code = "backend_error"


class NumericError(FinIRError):
    """A guarded numeric condition (div-by-zero, NaN, inf) was hit in strict mode."""

    code = "numeric_error"


class ExecutionError(FinIRError):
    """A runtime evaluation failure not covered by a more specific error."""

    code = "execution_error"
