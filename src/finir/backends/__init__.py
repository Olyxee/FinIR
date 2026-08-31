"""Execution backends: reference/CPU (NumPy), optional GPU (CuPy), and dispatch."""

from __future__ import annotations

from .base import ExecutionBackend
from .dispatch import BackendChoice, BackendPlanner, WorkloadProfile
from .gpu import GpuBackend, gpu_available
from .numpy_backend import NumpyBackend, ReferenceBackend

__all__ = [
    "BackendChoice",
    "BackendPlanner",
    "ExecutionBackend",
    "GpuBackend",
    "NumpyBackend",
    "ReferenceBackend",
    "WorkloadProfile",
    "gpu_available",
]
