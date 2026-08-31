"""FinIR intermediate representation: modules, expressions, parsing, serialization."""

from __future__ import annotations

from .expr import Bin, Call, Expr, Lit, Ref, expr_to_text, free_refs
from .module import Computed, Constant, Input, Module, Node
from .parser import parse_expr, parse_module
from .serialize import module_from_json, module_to_json
from .textual import module_to_text
from .typeinfer import infer_module_types
from .validate import validate_module

__all__ = [
    "Bin",
    "Call",
    "Computed",
    "Constant",
    "Expr",
    "Input",
    "Lit",
    "Module",
    "Node",
    "Ref",
    "expr_to_text",
    "free_refs",
    "infer_module_types",
    "module_from_json",
    "module_to_json",
    "module_to_text",
    "parse_expr",
    "parse_module",
    "validate_module",
]
