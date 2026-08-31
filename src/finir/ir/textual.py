"""Render a FinIR module to its textual ``.finir`` form."""

from __future__ import annotations

from .expr import expr_to_text
from .module import Computed, Constant, Input, Module


def module_to_text(module: Module) -> str:
    """Render a module in the block ``model NAME { ... }`` form."""
    lines = [f"model {module.name} {{"]
    for node in module.iter_nodes():
        if isinstance(node, Input):
            default = f"  = {node.default:g}" if node.default is not None else ""
            lines.append(f"  input {node.name}: {node.type.textual()}{default}")
        elif isinstance(node, Constant):
            lines.append(f"  const {node.name} = {node.value:g} : {node.type.textual()}")
        elif isinstance(node, Computed):
            typ = f"  : {node.type.textual()}" if node.type is not None else ""
            lines.append(f"  {node.name} = {expr_to_text(node.expr)}{typ}")
    for out in module.outputs:
        lines.append(f"  output {out}")
    lines.append("}")
    return "\n".join(lines)
