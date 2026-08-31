"""Reference and vectorized-CPU backends (NumPy).

``NumpyBackend`` is the reference implementation: it always works, on any machine,
with no optional dependencies beyond NumPy. It handles both scalar graphs (Python
floats / NumPy scalars) and large scenario batches (NumPy arrays) through the same
code — NumPy broadcasting does the vectorization.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .base import ExecutionBackend


class NumpyBackend(ExecutionBackend):
    """Scalar + vectorized CPU backend."""

    name = "cpu"

    def prepare(self, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            return np.asarray(value, dtype="float64")
        return value

    def finalize(self, value: Any) -> Any:
        if isinstance(value, np.ndarray) and value.ndim == 0:
            return float(value)
        return value

    def binary(self, op: str, a: Any, b: Any) -> Any:
        return self._apply(op, a, b)


# The reference backend is the same class used in a strictly-scalar mode; the engine
# simply feeds it scalars. We expose an alias for clarity in the dispatch layer.
ReferenceBackend = NumpyBackend
