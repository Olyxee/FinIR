"""Compiler pass tests: constant folding, DCE, CSE, dependency, pipeline."""

from __future__ import annotations

from finir.compiler import compile_module
from finir.compiler.passes import (
    CompileReport,
    pass_constant_fold,
    pass_cse,
    pass_dead_code_elim,
)
from finir.ir import parse_module
from finir.ir.expr import Lit
from finir.kernels.registry import default_registry


def test_constant_folding_folds_constants():
    m = parse_module("model m { const a = 2\n const b = 3\n c = a * b + 1\n output c }")
    report = CompileReport()
    out = pass_constant_fold(m, report, default_registry())
    node = out.nodes["c"]
    assert isinstance(node.expr, Lit)
    assert node.expr.value == 7  # 2*3 + 1
    assert report.details["constant_folding"]["folded_nodes"] == 1


def test_dead_code_elimination_removes_unreachable():
    m = parse_module(
        "model m { input a: scalar\n input b: scalar\n used = a + 1\n unused = b * 5\n output used }"
    )
    report = CompileReport()
    out = pass_dead_code_elim(m, report)
    assert "unused" not in out.nodes
    assert "used" in out.nodes
    assert report.details["dead_node_elimination"]["removed"] == 2  # unused + b


def test_cse_hoists_repeated_subexpression():
    # (a + b) appears in two nodes -> hoisted once.
    m = parse_module(
        "model m { input a: scalar\n input b: scalar\n x = a + b\n y = (a + b) * 2\n output x\n output y }"
    )
    report = CompileReport()
    out = pass_cse(m, report)
    assert report.details["common_subexpression_elimination"]["hoisted"] >= 1
    assert any(n.startswith("_cse_") for n in out.nodes)


def test_full_pipeline_reports_all_passes():
    m = parse_module(
        "model m { input revenue: money[ZAR]\n input cogs: money[ZAR]\n gp = revenue - cogs\n output gp }"
    )
    compiled = compile_module(m)
    for p in ["validation", "type_check", "constant_folding", "dead_node_elimination"]:
        assert p in compiled.report.passes
    assert compiled.types["gp"].textual() == "money[ZAR]"
