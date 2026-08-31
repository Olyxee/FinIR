"""Optional GPU backend (CuPy).

Never a hard dependency. If CuPy + a CUDA device are present, arithmetic-graph
scenario batches run on the GPU; otherwise ``available`` is False and the dispatch
planner falls back to CPU. Named kernels (NPV, risk, ...) are evaluated on the host
and their results moved back to the device, so correctness never depends on a GPU
implementation of every kernel.
"""

from __future__ import annotations

from typing import Any

from ..kernels.registry import KernelRegistry
from .base import ExecutionBackend

try:  # pragma: no cover - exercised only where CuPy is installed
    import cupy as _cp

    _CUPY_OK = True
except Exception:
    _cp = None
    _CUPY_OK = False


class GpuBackend(ExecutionBackend):
    """CuPy-backed GPU execution for arithmetic-heavy scenario batches."""

    name = "gpu"

    def __init__(self) -> None:
        self._cp = _cp

    @property
    def available(self) -> bool:
        if not _CUPY_OK or self._cp is None:
            return False
        try:  # pragma: no cover - hardware dependent
            return self._cp.cuda.runtime.getDeviceCount() > 0
        except Exception:
            return False

    def prepare(self, value: Any) -> Any:  # pragma: no cover - hardware dependent
        return self._cp.asarray(value)

    def finalize(self, value: Any) -> Any:  # pragma: no cover - hardware dependent
        return self._cp.asnumpy(value)

    def binary(self, op: str, a: Any, b: Any) -> Any:  # pragma: no cover - hardware dependent
        return self._apply(op, a, b)

    def call_kernel(  # pragma: no cover - hardware dependent
        self, kernels: KernelRegistry, name: str, args: list[Any]
    ) -> Any:
        # Named kernels are CPU/NumPy; round-trip host<->device.
        host_args = [self._cp.asnumpy(a) if hasattr(a, "device") else a for a in args]
        result = kernels.call(name, host_args)
        return self._cp.asarray(result)


def gpu_available() -> bool:
    """Whether a usable CuPy GPU backend is present (safe to call anywhere)."""
    return GpuBackend().available
