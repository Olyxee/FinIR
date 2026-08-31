"""IR parsing, serialization, textual form, and validation tests."""

from __future__ import annotations

import pytest

from finir.exceptions import ParseError, ValidationError
from finir.ir import (
    infer_module_types,
    module_from_json,
    module_to_json,
    module_to_text,
    parse_expr,
    parse_module,
    validate_module,
)
from finir.ir.expr import Bin, Call, Lit, free_refs

SRC = """
model demo {
  input revenue: money[ZAR]
  input cogs: money[ZAR]
  const tax_rate = 0.28
  gross_profit = revenue - cogs
  gross_margin = gross_profit / revenue
  output gross_margin
}
"""


def test_parse_module_nodes():
    m = parse_module(SRC)
    assert set(m.nodes) == {"revenue", "cogs", "tax_rate", "gross_profit", "gross_margin"}
    assert m.outputs == ["gross_margin"]


def test_parse_expr_forms():
    e = parse_expr("revenue - cogs * 2")
    assert isinstance(e, Bin) and e.op == "-"
    assert isinstance(e.right, Bin) and e.right.op == "*"  # precedence
    assert free_refs(e) == {"revenue", "cogs"}


def test_parse_expr_percentage_literal():
    e = parse_expr("4%")
    assert isinstance(e, Lit) and abs(e.value - 0.04) < 1e-9


def test_parse_expr_call():
    e = parse_expr("npv(rate, cashflows)")
    assert isinstance(e, Call) and e.func == "npv" and len(e.args) == 2


def test_json_roundtrip():
    m = parse_module(SRC)
    m2 = module_from_json(module_to_json(m))
    assert module_to_text(m2) == module_to_text(m)


def test_topo_and_deps():
    m = parse_module(SRC)
    assert m.dependencies("gross_margin") == ["gross_profit", "revenue"]
    order = m.topo_order()
    assert order.index("gross_profit") < order.index("gross_margin")


def test_validate_unknown_reference():
    m = parse_module("model m { input a: scalar\n b = a + missing }")
    with pytest.raises(ValidationError):
        validate_module(m)


def test_validate_cycle():
    m = parse_module("model m { input a: scalar\n b = a + c\n c = b + a\n output b }")
    with pytest.raises(ValidationError):
        m.topo_order()


def test_parse_bad_statement():
    with pytest.raises(ParseError):
        parse_module("model m { this is not valid }")


def test_infer_types_on_module():
    m = parse_module(SRC)
    types = infer_module_types(m)
    assert types["gross_profit"].textual() == "money[ZAR]"
    assert types["gross_margin"].textual() == "ratio"
