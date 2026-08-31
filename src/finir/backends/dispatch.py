"""Workload-aware backend dispatch (item 14).

A tiny cost model chooses a backend from the shape of the work: scalar graphs and
small batches run on the CPU; very large scenario batches use the GPU when one is
available. The thresholds are heuristics — they are meant to be *measured*
(research/experiment_002_backend_dispatch.md) and tuned, not asserted.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ExecutionBackend
from .gpu import GpuBackend
from .numpy_backend import NumpyBackend

# Default thresholds (elements in the scenario dimension). Calibrate empirically.
GPU_MIN_ELEMENTS = 250_000


@dataclass
class WorkloadProfile:
    """What we know about the work before choosing hardware."""

    scenario_size: int = 1  # number of elements along the scenario dimension
    node_count: int = 0
    has_named_kernels: bool = False


@dataclass
class BackendChoice:
    backend: ExecutionBackend
    rationale: str


class BackendPlanner:
    """Chooses an execution backend for a workload."""

    def __init__(self, *, gpu_min_elements: int = GPU_MIN_ELEMENTS) -> None:
        self.gpu_min_elements = gpu_min_elements
        self._cpu = NumpyBackend()
        self._gpu = GpuBackend()

    def choose(self, workload: WorkloadProfile) -> BackendChoice:
        if workload.scenario_size >= self.gpu_min_elements and self._gpu.available:
            return BackendChoice(
                self._gpu,
                f"scenario_size={workload.scenario_size} >= {self.gpu_min_elements} and GPU available",
            )
        if workload.scenario_size >= self.gpu_min_elements:
            return BackendChoice(
                self._cpu,
                f"scenario_size={workload.scenario_size} large but no GPU; vectorized CPU",
            )
        if workload.scenario_size > 1:
            return BackendChoice(self._cpu, "vectorized CPU for a scenario batch")
        return BackendChoice(self._cpu, "scalar CPU for a small graph")

    def get(self, name: str) -> ExecutionBackend:
        if name in ("cpu", "reference", "numpy"):
            return self._cpu
        if name == "gpu":
            return self._gpu
        raise ValueError(f"unknown backend {name!r}")
