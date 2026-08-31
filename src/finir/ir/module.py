"""The FinIR module: the typed computation graph.

A module is an ordered collection of named nodes — inputs, constants, and computed
nodes (each defined by an :class:`Expr`) — plus a set of declared outputs. It is a
pure data structure: dependency analysis, type inference, compilation, and
execution all operate over it without mutating it (compiler passes return new
modules).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from ..exceptions import ValidationError
from ..types import FinType
from .expr import Expr, Ref, free_refs


@dataclass
class Input:
    """A named model input with a type and an optional default value."""

    name: str
    type: FinType
    default: float | None = None


@dataclass
class Constant:
    """A named constant value."""

    name: str
    value: float
    type: FinType


@dataclass
class Computed:
    """A node defined by an expression over other nodes."""

    name: str
    expr: Expr
    type: FinType | None = None  # inferred by the type-checker pass


Node = Input | Constant | Computed


@dataclass
class Module:
    """A typed financial computation graph."""

    name: str = "model"
    nodes: dict[str, Node] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)  # insertion order
    outputs: list[str] = field(default_factory=list)

    # -- construction --------------------------------------------------------
    def add(self, node: Node) -> Node:
        if node.name in self.nodes:
            raise ValidationError(f"duplicate node name: {node.name!r}")
        self.nodes[node.name] = node
        self.order.append(node.name)
        return node

    def replace(self, node: Node) -> None:
        if node.name not in self.nodes:
            raise ValidationError(f"cannot replace unknown node {node.name!r}")
        self.nodes[node.name] = node

    def remove(self, name: str) -> None:
        self.nodes.pop(name, None)
        if name in self.order:
            self.order.remove(name)
        if name in self.outputs:
            self.outputs.remove(name)

    def set_output(self, name: str) -> None:
        if name not in self.nodes:
            raise ValidationError(f"unknown output node {name!r}")
        if name not in self.outputs:
            self.outputs.append(name)

    # -- queries -------------------------------------------------------------
    def get(self, name: str) -> Node:
        if name not in self.nodes:
            raise ValidationError(f"unknown node {name!r}")
        return self.nodes[name]

    def dependencies(self, name: str) -> list[str]:
        """Direct dependencies (referenced node names) of a node."""
        node = self.get(name)
        if isinstance(node, Computed):
            return [r for r in sorted(free_refs(node.expr))]
        return []

    def dependents(self, name: str) -> list[str]:
        """Nodes that directly reference ``name``."""
        out = []
        for other in self.order:
            if name in self.dependencies(other):
                out.append(other)
        return out

    def inputs(self) -> list[Input]:
        return [n for n in self.iter_nodes() if isinstance(n, Input)]

    def computed(self) -> list[Computed]:
        return [n for n in self.iter_nodes() if isinstance(n, Computed)]

    def iter_nodes(self):
        for name in self.order:
            yield self.nodes[name]

    # -- ordering ------------------------------------------------------------
    def topo_order(self) -> list[str]:
        """Return node names in dependency order (Kahn's algorithm)."""
        indeg: dict[str, int] = dict.fromkeys(self.order, 0)
        adj: dict[str, list[str]] = {n: [] for n in self.order}
        for n in self.order:
            for dep in self.dependencies(n):
                if dep not in self.nodes:
                    raise ValidationError(f"node {n!r} references unknown node {dep!r}")
                adj[dep].append(n)
                indeg[n] += 1
        # Stable order: process in insertion order among ready nodes.
        ready = deque(n for n in self.order if indeg[n] == 0)
        out: list[str] = []
        while ready:
            n = ready.popleft()
            out.append(n)
            for m in adj[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
        if len(out) != len(self.order):
            cycle = [n for n in self.order if n not in out]
            raise ValidationError(f"dependency cycle involving: {cycle}")
        return out

    def transitive_dependents(self, changed: set[str]) -> set[str]:
        """All nodes reachable downstream from the changed set (incl. themselves)."""
        adj: dict[str, list[str]] = {n: [] for n in self.order}
        for n in self.order:
            for dep in self.dependencies(n):
                adj.setdefault(dep, []).append(n)
        seen: set[str] = set()
        stack = list(changed)
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for m in adj.get(cur, []):
                if m not in seen:
                    stack.append(m)
        return seen

    def clone(self) -> Module:
        """A shallow-structural copy (nodes are dataclasses; exprs are immutable)."""
        m = Module(name=self.name)
        for name in self.order:
            node = self.nodes[name]
            if isinstance(node, Input):
                m.add(Input(node.name, node.type, node.default))
            elif isinstance(node, Constant):
                m.add(Constant(node.name, node.value, node.type))
            else:
                m.add(Computed(node.name, node.expr, node.type))
        m.outputs = list(self.outputs)
        return m


def make_ref(name: str) -> Ref:
    return Ref(name)
