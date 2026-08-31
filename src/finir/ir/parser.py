"""Parser for FinIR expressions and the ``.finir`` textual module format.

Expression grammar (precedence-climbing):

    expr    := term (('+' | '-') term)*
    term    := factor (('*' | '/') factor)*
    factor  := NUMBER | NUMBER '%' | IDENT | IDENT '(' args ')' | '(' expr ')' | '-' factor

Module format (either the block form or bare lines):

    model company {
      input revenue: money[ZAR]
      const tax_rate = 0.28
      gross_profit = revenue - cogs
      output gross_profit
    }
"""

from __future__ import annotations

import re

from ..exceptions import ParseError
from ..types import Percentage, Scalar, parse_type
from .expr import Bin, Call, Expr, Lit, Ref
from .module import Computed, Constant, Input, Module

_TOKEN_RE = re.compile(
    r"""
    (?P<NUMBER>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)
    | (?P<IDENT>[A-Za-z_][A-Za-z0-9_.]*)
    | (?P<OP>[+\-*/])
    | (?P<PCT>%)
    | (?P<LP>\()
    | (?P<RP>\))
    | (?P<COMMA>,)
    | (?P<WS>\s+)
    """,
    re.VERBOSE,
)


class _Tokens:
    def __init__(self, text: str) -> None:
        self.toks: list[tuple[str, str]] = []
        pos = 0
        while pos < len(text):
            m = _TOKEN_RE.match(text, pos)
            if not m:
                raise ParseError(f"unexpected character at {pos}: {text[pos : pos + 10]!r}")
            pos = m.end()
            kind = m.lastgroup
            if kind is None or kind == "WS":
                continue
            self.toks.append((kind, m.group()))
        self.i = 0

    def peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def next(self) -> tuple[str, str]:
        if self.i >= len(self.toks):
            raise ParseError("unexpected end of expression")
        tok = self.toks[self.i]
        self.i += 1
        return tok


def parse_expr(text: str) -> Expr:
    """Parse a single expression string into an :class:`Expr`."""
    toks = _Tokens(text)
    expr = _parse_add(toks)
    if toks.peek() is not None:
        raise ParseError(f"trailing tokens in expression: {text!r}")
    return expr


def _parse_add(toks: _Tokens) -> Expr:
    left = _parse_mul(toks)
    while (t := toks.peek()) and t[0] == "OP" and t[1] in "+-":
        op = toks.next()[1]
        right = _parse_mul(toks)
        left = Bin(op, left, right)
    return left


def _parse_mul(toks: _Tokens) -> Expr:
    left = _parse_factor(toks)
    while (t := toks.peek()) and t[0] == "OP" and t[1] in "*/":
        op = toks.next()[1]
        right = _parse_factor(toks)
        left = Bin(op, left, right)
    return left


def _parse_factor(toks: _Tokens) -> Expr:
    t = toks.peek()
    if t is None:
        raise ParseError("unexpected end of expression")
    if t[0] == "OP" and t[1] == "-":
        toks.next()
        return Bin("-", Lit(0.0, Scalar()), _parse_factor(toks))
    if t[0] == "LP":
        toks.next()
        expr = _parse_add(toks)
        closing = toks.next()
        if closing[0] != "RP":
            raise ParseError("expected ')'")
        return expr
    if t[0] == "NUMBER":
        toks.next()
        value = float(t[1])
        nxt = toks.peek()
        if nxt and nxt[0] == "PCT":
            toks.next()
            return Lit(value / 100.0, Percentage())
        return Lit(value, Scalar())
    if t[0] == "IDENT":
        toks.next()
        nxt = toks.peek()
        if nxt and nxt[0] == "LP":
            toks.next()
            args = _parse_args(toks)
            return Call(t[1], tuple(args))
        return Ref(t[1])
    raise ParseError(f"unexpected token {t[1]!r}")


def _parse_args(toks: _Tokens) -> list[Expr]:
    args: list[Expr] = []
    if (t := toks.peek()) and t[0] == "RP":
        toks.next()
        return args
    while True:
        args.append(_parse_add(toks))
        t = toks.next()
        if t[0] == "RP":
            break
        if t[0] != "COMMA":
            raise ParseError("expected ',' or ')' in call arguments")
    return args


# --------------------------------------------------------------------------- module
def parse_module(text: str, *, name: str = "model") -> Module:
    """Parse a ``.finir`` textual module (block form or bare lines)."""
    text = _strip_comments(text)
    module_name = name
    block = re.match(r"\s*model\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{(.*)\}\s*$", text, re.DOTALL)
    if block:
        module_name = block.group(1)
        text = block.group(2)

    module = Module(name=module_name)
    statements = [s.strip() for s in re.split(r"[\n;]", text) if s.strip()]
    for stmt in statements:
        _parse_statement(module, stmt)
    return module


def _strip_comments(text: str) -> str:
    out_lines = []
    for line in text.splitlines():
        for marker in ("#", "//"):
            idx = line.find(marker)
            if idx != -1:
                line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


def _parse_statement(module: Module, stmt: str) -> None:
    # output NAME[, NAME...]
    if stmt.startswith("output "):
        for nm in stmt[len("output ") :].split(","):
            module.set_output(nm.strip())
        return
    # input NAME: TYPE
    m = re.match(r"input\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$", stmt)
    if m:
        module.add(Input(m.group(1), parse_type(m.group(2).strip())))
        return
    # const NAME = VALUE [: TYPE]
    m = re.match(r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([-\d.eE]+)\s*(?::\s*(.+))?$", stmt)
    if m:
        typ = parse_type(m.group(3).strip()) if m.group(3) else Scalar()
        module.add(Constant(m.group(1), float(m.group(2)), typ))
        return
    # NAME = input TYPE   (alternate input form)
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*input\s+(.+)$", stmt)
    if m:
        module.add(Input(m.group(1), parse_type(m.group(2).strip())))
        return
    # NAME = EXPR   (computed)
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$", stmt)
    if m:
        module.add(Computed(m.group(1), parse_expr(m.group(2))))
        return
    raise ParseError(f"could not parse statement: {stmt!r}")
