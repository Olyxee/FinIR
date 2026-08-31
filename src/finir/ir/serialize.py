"""JSON serialization for FinIR modules.

The JSON form is the stable, language-neutral interchange format (item 32): other
languages can consume a FinIR module without a Python parser. Types round-trip via
their textual form; expressions round-trip structurally.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import ParseError
from ..types import parse_type
from ..version import IR_SCHEMA_VERSION
from .expr import Bin, Call, Expr, Lit, Ref
from .module import Computed, Constant, Input, Module


def expr_to_json(expr: Expr) -> dict[str, Any]:
    if isinstance(expr, Ref):
        return {"k": "ref", "name": expr.name}
    if isinstance(expr, Lit):
        return {"k": "lit", "value": expr.value, "type": expr.type.textual()}
    if isinstance(expr, Bin):
        return {
            "k": "bin",
            "op": expr.op,
            "l": expr_to_json(expr.left),
            "r": expr_to_json(expr.right),
        }
    if isinstance(expr, Call):
        return {"k": "call", "func": expr.func, "args": [expr_to_json(a) for a in expr.args]}
    raise TypeError(f"unknown expr {expr!r}")


def expr_from_json(obj: dict[str, Any]) -> Expr:
    k = obj["k"]
    if k == "ref":
        return Ref(obj["name"])
    if k == "lit":
        return Lit(float(obj["value"]), parse_type(obj["type"]))
    if k == "bin":
        return Bin(obj["op"], expr_from_json(obj["l"]), expr_from_json(obj["r"]))
    if k == "call":
        return Call(obj["func"], tuple(expr_from_json(a) for a in obj["args"]))
    raise ParseError(f"unknown expr node kind {k!r}")


def module_to_json(module: Module) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for node in module.iter_nodes():
        if isinstance(node, Input):
            nodes.append(
                {
                    "kind": "input",
                    "name": node.name,
                    "type": node.type.textual(),
                    "default": node.default,
                }
            )
        elif isinstance(node, Constant):
            nodes.append(
                {
                    "kind": "const",
                    "name": node.name,
                    "type": node.type.textual(),
                    "value": node.value,
                }
            )
        elif isinstance(node, Computed):
            nodes.append(
                {
                    "kind": "computed",
                    "name": node.name,
                    "expr": expr_to_json(node.expr),
                    "type": node.type.textual() if node.type is not None else None,
                }
            )
    return {
        "finir_schema": IR_SCHEMA_VERSION,
        "name": module.name,
        "nodes": nodes,
        "outputs": list(module.outputs),
    }


def module_from_json(obj: dict[str, Any]) -> Module:
    module = Module(name=obj.get("name", "model"))
    for nd in obj["nodes"]:
        kind = nd["kind"]
        if kind == "input":
            module.add(Input(nd["name"], parse_type(nd["type"]), nd.get("default")))
        elif kind == "const":
            module.add(Constant(nd["name"], float(nd["value"]), parse_type(nd["type"])))
        elif kind == "computed":
            typ = parse_type(nd["type"]) if nd.get("type") else None
            module.add(Computed(nd["name"], expr_from_json(nd["expr"]), typ))
        else:
            raise ParseError(f"unknown node kind {kind!r}")
    for out in obj.get("outputs", []):
        module.set_output(out)
    return module
