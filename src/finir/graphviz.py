"""Graph export for FinIR modules (item 20): Graphviz DOT and JSON.

No website, no server — just a dependency-free DOT string (and JSON) you can pipe
into Graphviz. Optional SVG rendering uses the ``graphviz`` package if installed.
"""

from __future__ import annotations

from typing import Any

from .ir.module import Computed, Constant, Input, Module


def to_dot(module: Module, *, types: dict[str, Any] | None = None) -> str:
    """Render the module's dependency graph as Graphviz DOT."""
    lines = [f'digraph "{module.name}" {{', "  rankdir=LR;", "  node [fontname=Helvetica];"]
    for node in module.iter_nodes():
        label = node.name
        if types and node.name in types:
            label = f"{node.name}\\n{types[node.name].textual()}"
        if isinstance(node, Input):
            shape, color = "box", "#cde"
        elif isinstance(node, Constant):
            shape, color = "box", "#eee"
        else:
            shape, color = "ellipse", "#dfd" if node.name in module.outputs else "white"
        lines.append(
            f'  "{node.name}" [label="{label}", shape={shape}, style=filled, fillcolor="{color}"];'
        )
    for node in module.iter_nodes():
        if isinstance(node, Computed):
            for dep in module.dependencies(node.name):
                lines.append(f'  "{dep}" -> "{node.name}";')
    lines.append("}")
    return "\n".join(lines)


def to_graph_json(module: Module, *, types: dict[str, Any] | None = None) -> dict[str, Any]:
    nodes = []
    for node in module.iter_nodes():
        kind = (
            "input"
            if isinstance(node, Input)
            else "const"
            if isinstance(node, Constant)
            else "computed"
        )
        nodes.append(
            {
                "id": node.name,
                "kind": kind,
                "type": (types[node.name].textual() if types and node.name in types else None),
                "output": node.name in module.outputs,
            }
        )
    edges = [
        {"from": dep, "to": n.name}
        for n in module.iter_nodes()
        if isinstance(n, Computed)
        for dep in module.dependencies(n.name)
    ]
    return {"name": module.name, "nodes": nodes, "edges": edges}


def render_svg(module: Module, out_path: str) -> str | None:
    """Render an SVG if the optional ``graphviz`` package is available, else None."""
    try:
        import graphviz
    except Exception:
        return None
    src = graphviz.Source(to_dot(module))
    return src.render(out_path, format="svg", cleanup=True)
