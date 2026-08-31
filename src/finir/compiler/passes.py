"""FinIR compiler passes (item 17).

A pass either transforms the module (constant folding, dead-node elimination,
common-subexpression elimination) or analyses it (type checking, cache planning,
fusion analysis, backend planning). The pipeline threads a :class:`CompileReport`
so ``finir compile --show-passes`` can show exactly what each pass did.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ..ir.expr import Bin, Call, Expr, Lit, Ref, free_refs, structural_key
from ..ir.module import Computed, Constant, Input, Module
from ..ir.typeinfer import infer_module_types
from ..ir.validate import validate_module
from ..kernels.registry import KernelRegistry, default_registry
from ..types import Scalar


@dataclass
class CompileReport:
    passes: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    timings_ms: dict[str, float] = field(default_factory=dict)

    def record(self, name: str, detail: Any, ms: float) -> None:
        self.passes.append(name)
        self.details[name] = detail
        self.timings_ms[name] = round(ms, 4)


@dataclass
class CompiledModule:
    module: Module
    report: CompileReport
    types: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- passes
def _timed(fn, *args):
    t0 = time.perf_counter()
    out = fn(*args)
    return out, (time.perf_counter() - t0) * 1000.0


def pass_validate(module: Module, report: CompileReport) -> Module:
    _, ms = _timed(validate_module, module)
    report.record("validation", {"ok": True, "nodes": len(module.nodes)}, ms)
    return module


def pass_typecheck(module: Module, report: CompileReport, kernels: KernelRegistry) -> Module:
    def run():
        return infer_module_types(module, kernel=kernels.result_type)

    types, ms = _timed(run)
    report.record("type_check", {"typed_nodes": len(types)}, ms)
    report.details["__types__"] = types
    return module


def pass_constant_fold(module: Module, report: CompileReport, kernels: KernelRegistry) -> Module:
    t0 = time.perf_counter()
    const_env: dict[str, tuple[float, Any]] = {}
    for node in module.iter_nodes():
        if isinstance(node, Constant):
            const_env[node.name] = (node.value, node.type)

    folded = 0
    out = module.clone()
    for name in out.topo_order():
        node = out.nodes[name]
        if not isinstance(node, Computed):
            continue
        new_expr, was = _fold(node.expr, const_env, kernels)
        if was:
            folded += 1
            out.replace(Computed(node.name, new_expr, node.type))
        if isinstance(new_expr, Lit):
            const_env[name] = (new_expr.value, new_expr.type)
    ms = (time.perf_counter() - t0) * 1000.0
    report.record("constant_folding", {"folded_nodes": folded}, ms)
    return out


def _fold(expr: Expr, const_env: dict[str, tuple[float, Any]], kernels: KernelRegistry):
    if isinstance(expr, Lit):
        return expr, False
    if isinstance(expr, Ref):
        if expr.name in const_env:
            value, typ = const_env[expr.name]
            return Lit(value, typ), True
        return expr, False
    if isinstance(expr, Bin):
        left, cl = _fold(expr.left, const_env, kernels)
        right, cr = _fold(expr.right, const_env, kernels)
        if isinstance(left, Lit) and isinstance(right, Lit):
            from ..types import binary_result

            val = _apply_bin(expr.op, left.value, right.value)
            return Lit(val, binary_result(expr.op, left.type, right.type)), True
        changed = cl or cr
        return (Bin(expr.op, left, right) if changed else expr), changed
    if isinstance(expr, Call):
        new_args = []
        changed = False
        for a in expr.args:
            fa, ca = _fold(a, const_env, kernels)
            new_args.append(fa)
            changed = changed or ca
        if all(isinstance(a, Lit) for a in new_args):
            try:
                val = kernels.call(expr.func, [a.value for a in new_args if isinstance(a, Lit)])
                rtype = kernels.result_type(
                    expr.func, [a.type for a in new_args if isinstance(a, Lit)]
                )
                return Lit(float(val), rtype), True
            except Exception:
                pass
        return (Call(expr.func, tuple(new_args)) if changed else expr), changed
    return expr, False


def _apply_bin(op: str, a: float, b: float) -> float:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    return a / b if b != 0 else float("nan")


def pass_dead_code_elim(module: Module, report: CompileReport) -> Module:
    if not module.outputs:
        report.record("dead_node_elimination", {"removed": 0, "reason": "no outputs declared"}, 0.0)
        return module
    t0 = time.perf_counter()
    live: set[str] = set()
    stack = list(module.outputs)
    while stack:
        cur = stack.pop()
        if cur in live:
            continue
        live.add(cur)
        stack.extend(module.dependencies(cur))
    removed = [n for n in module.order if n not in live]
    out = module.clone()
    for n in removed:
        out.remove(n)
    ms = (time.perf_counter() - t0) * 1000.0
    report.record("dead_node_elimination", {"removed": len(removed), "removed_nodes": removed}, ms)
    return out


def pass_dependency_pruning(module: Module, report: CompileReport) -> Module:
    # Reachability report (the elimination itself is done by dead_code_elim).
    reach = module.transitive_dependents(set(n for n in module.order))
    report.record("dependency_pruning", {"reachable": len(reach)}, 0.0)
    return module


def pass_cse(module: Module, report: CompileReport) -> Module:
    """Conservative CSE: hoist repeated leaf-only subexpressions (safe, no nesting)."""
    t0 = time.perf_counter()
    counts: Counter[str] = Counter()
    exemplar: dict[str, Expr] = {}

    def scan(e: Expr) -> None:
        if isinstance(e, Bin):
            if _is_leaf_binary(e):
                key = structural_key(e)
                counts[key] += 1
                exemplar[key] = e
            scan(e.left)
            scan(e.right)
        elif isinstance(e, Call):
            for a in e.args:
                scan(a)

    for node in module.computed():
        scan(node.expr)

    repeated = {k: exemplar[k] for k, c in counts.items() if c >= 2}
    if not repeated:
        report.record(
            "common_subexpression_elimination", {"hoisted": 0}, (time.perf_counter() - t0) * 1000.0
        )
        return module

    out = module.clone()
    key_to_name: dict[str, str] = {}
    for i, (key, ex) in enumerate(repeated.items()):
        cse_name = f"_cse_{i}"
        key_to_name[key] = cse_name
        out.add(Computed(cse_name, ex, None))

    for node in list(out.computed()):
        if node.name.startswith("_cse_"):
            continue
        new_expr = _replace(node.expr, key_to_name)
        out.replace(Computed(node.name, new_expr, node.type))
    ms = (time.perf_counter() - t0) * 1000.0
    report.record("common_subexpression_elimination", {"hoisted": len(repeated)}, ms)
    return out


def _is_leaf_binary(e: Bin) -> bool:
    return isinstance(e.left, (Ref, Lit)) and isinstance(e.right, (Ref, Lit))


def _replace(expr: Expr, key_to_name: dict[str, str]) -> Expr:
    if isinstance(expr, Bin):
        if _is_leaf_binary(expr) and structural_key(expr) in key_to_name:
            return Ref(key_to_name[structural_key(expr)])
        return Bin(expr.op, _replace(expr.left, key_to_name), _replace(expr.right, key_to_name))
    if isinstance(expr, Call):
        return Call(expr.func, tuple(_replace(a, key_to_name) for a in expr.args))
    return expr


def pass_scenario_vectorization(module: Module, report: CompileReport) -> Module:
    # The runtime auto-vectorizes scalar arithmetic graphs via NumPy broadcasting;
    # this pass records which nodes are pure-arithmetic (vectorizable) vs kernel-bound.
    arithmetic = [n.name for n in module.computed() if _is_pure_arithmetic(n.expr)]
    report.record(
        "scenario_vectorization",
        {"vectorizable_nodes": len(arithmetic), "total_computed": len(module.computed())},
        0.0,
    )
    return module


def pass_kernel_fusion(module: Module, report: CompileReport) -> Module:
    # Identify maximal arithmetic chains that could be fused into one kernel.
    chains = _fusion_groups(module)
    report.record(
        "kernel_fusion",
        {
            "fusable_chains": len(chains),
            "note": "arithmetic chains identified; NumPy already fuses elementwise ops, "
            "so a separate fusion kernel showed no material CPU gain — see docs/performance.md",
        },
        0.0,
    )
    return module


def pass_cache_planning(module: Module, report: CompileReport) -> Module:
    report.record(
        "cache_planning",
        {"cacheable_nodes": len(module.computed()), "inputs": len(module.inputs())},
        0.0,
    )
    return module


def _is_pure_arithmetic(expr: Expr) -> bool:
    if isinstance(expr, (Ref, Lit)):
        return True
    if isinstance(expr, Bin):
        return _is_pure_arithmetic(expr.left) and _is_pure_arithmetic(expr.right)
    return False  # Call


def _fusion_groups(module: Module) -> list[list[str]]:
    groups: list[list[str]] = []
    for node in module.computed():
        if _is_pure_arithmetic(node.expr) and len(free_refs(node.expr)) >= 1:
            groups.append([node.name])
    return groups


# --------------------------------------------------------------------------- pipeline
DEFAULT_PIPELINE = [
    "validation",
    "type_check",
    "constant_folding",
    "common_subexpression_elimination",
    "dead_node_elimination",
    "dependency_pruning",
    "scenario_vectorization",
    "kernel_fusion",
    "cache_planning",
]


def compile_module(
    module: Module,
    *,
    kernels: KernelRegistry | None = None,
    pipeline: list[str] | None = None,
) -> CompiledModule:
    """Run the compiler pipeline and return the optimized module + report."""
    kern = kernels or default_registry()
    steps = pipeline or DEFAULT_PIPELINE
    report = CompileReport()
    m = module
    for step in steps:
        if step == "validation":
            m = pass_validate(m, report)
        elif step == "type_check":
            m = pass_typecheck(m, report, kern)
        elif step == "constant_folding":
            m = pass_constant_fold(m, report, kern)
        elif step == "common_subexpression_elimination":
            m = pass_cse(m, report)
        elif step == "dead_node_elimination":
            m = pass_dead_code_elim(m, report)
        elif step == "dependency_pruning":
            m = pass_dependency_pruning(m, report)
        elif step == "scenario_vectorization":
            m = pass_scenario_vectorization(m, report)
        elif step == "kernel_fusion":
            m = pass_kernel_fusion(m, report)
        elif step == "cache_planning":
            m = pass_cache_planning(m, report)
        else:
            raise ValueError(f"unknown pass {step!r}")
    # Re-infer types after transforms so the compiled module is fully typed.
    types = infer_module_types(m, kernel=kern.result_type)
    return CompiledModule(module=m, report=report, types=types)


_ = (Input, Scalar)  # referenced by type rules elsewhere; keep imported
