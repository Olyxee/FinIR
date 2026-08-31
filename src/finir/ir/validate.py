"""Structural validation of a FinIR module."""

from __future__ import annotations

from ..exceptions import ValidationError
from .expr import free_refs
from .module import Computed, Module


def validate_module(module: Module) -> None:
    """Check references resolve, outputs exist, and there are no cycles.

    Raises :class:`ValidationError` on the first problem found.
    """
    if not module.nodes:
        raise ValidationError("module has no nodes")
    for node in module.iter_nodes():
        if isinstance(node, Computed):
            for ref in free_refs(node.expr):
                if ref not in module.nodes:
                    raise ValidationError(f"node {node.name!r} references unknown node {ref!r}")
                if ref == node.name:
                    raise ValidationError(f"node {node.name!r} references itself")
    for out in module.outputs:
        if out not in module.nodes:
            raise ValidationError(f"output {out!r} is not a node")
    module.topo_order()  # raises on cycles
