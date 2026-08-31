"""The FinIR finance-aware type system.

Financial computation is unsafe when a system can add money to a day-count or mix
currencies silently. FinIR gives every value a type and enforces the algebra of
finance at compile time:

    money - money      -> money      (same currency; else CurrencyError)
    money / money      -> ratio
    money * percentage -> money
    money + days       -> TypeCheckError

Types are small frozen value objects with a stable textual form (``money[ZAR]``,
``percentage``, ``series[money[ZAR],month]``) used by the IR printer and parser.
``Series`` and ``ScenarioVector`` are wrappers carrying an inner element type;
arithmetic unwraps them, applies the element rule, and re-wraps.
"""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import CurrencyError, TypeCheckError


@dataclass(frozen=True)
class FinType:
    """Base class for FinIR types."""

    def textual(self) -> str:  # pragma: no cover - overridden
        return "type"

    def __str__(self) -> str:
        return self.textual()


@dataclass(frozen=True)
class Scalar(FinType):
    def textual(self) -> str:
        return "scalar"


@dataclass(frozen=True)
class Boolean(FinType):
    def textual(self) -> str:
        return "bool"


@dataclass(frozen=True)
class Money(FinType):
    currency: str

    def textual(self) -> str:
        return f"money[{self.currency}]"


@dataclass(frozen=True)
class Percentage(FinType):
    def textual(self) -> str:
        return "percentage"


@dataclass(frozen=True)
class Ratio(FinType):
    def textual(self) -> str:
        return "ratio"


@dataclass(frozen=True)
class Days(FinType):
    def textual(self) -> str:
        return "days"


@dataclass(frozen=True)
class Quantity(FinType):
    unit: str = "units"

    def textual(self) -> str:
        return f"quantity[{self.unit}]"


@dataclass(frozen=True)
class Rate(FinType):
    per: str = "year"

    def textual(self) -> str:
        return f"rate[{self.per}]"


@dataclass(frozen=True)
class Series(FinType):
    element: FinType
    period: str = "month"  # month | quarter | year | custom

    def textual(self) -> str:
        return f"series[{self.element.textual()},{self.period}]"


@dataclass(frozen=True)
class ScenarioVector(FinType):
    """A batch of values of ``element`` type across a scenario dimension."""

    element: FinType

    def textual(self) -> str:
        return f"scenario[{self.element.textual()}]"


# --------------------------------------------------------------------------- parsing
_SIMPLE = {
    "scalar": Scalar(),
    "percentage": Percentage(),
    "pct": Percentage(),
    "ratio": Ratio(),
    "days": Days(),
    "bool": Boolean(),
    "boolean": Boolean(),
}


def parse_type(text: str) -> FinType:
    """Parse a textual type such as ``money[ZAR]`` or ``series[money[ZAR],month]``."""
    text = text.strip()
    low = text.lower()
    if low in _SIMPLE:
        return _SIMPLE[low]
    if low.startswith("money[") and text.endswith("]"):
        return Money(text[len("money[") : -1].strip())
    if low.startswith("quantity[") and text.endswith("]"):
        return Quantity(text[len("quantity[") : -1].strip() or "units")
    if low.startswith("rate[") and text.endswith("]"):
        return Rate(text[len("rate[") : -1].strip() or "year")
    if low.startswith("series[") and text.endswith("]"):
        inner = text[len("series[") : -1]
        elem, _, period = inner.rpartition(",")
        return Series(parse_type(elem.strip()), (period.strip() or "month"))
    if low.startswith("scenario[") and text.endswith("]"):
        return ScenarioVector(parse_type(text[len("scenario[") : -1].strip()))
    if low == "money":
        return Money("ZAR")
    raise TypeCheckError(f"unknown type: {text!r}")


# --------------------------------------------------------------------------- algebra
_NUMERIC_LIKE = (Scalar, Percentage, Ratio, Rate)


def _unwrap(t: FinType) -> tuple[FinType, str | None]:
    """Return (element_type, wrapper) where wrapper is 'series','scenario', or None."""
    if isinstance(t, Series):
        return t.element, "series"
    if isinstance(t, ScenarioVector):
        return t.element, "scenario"
    return t, None


def _rewrap(
    elem: FinType, wa: tuple[FinType, str | None], wb: tuple[FinType, str | None]
) -> FinType:
    # ScenarioVector dominates Series dominates scalar element.
    for _, w in (wa, wb):
        if w == "scenario":
            return ScenarioVector(elem)
    for orig, w in (wa, wb):
        if w == "series":
            period = orig.period if isinstance(orig, Series) else "month"
            return Series(elem, period)
    return elem


def binary_result(op: str, a: FinType, b: FinType) -> FinType:
    """Return the result type of ``a op b`` or raise a TypeCheckError/CurrencyError."""
    wa, wb = _unwrap(a), _unwrap(b)
    elem = _element_binary(op, wa[0], wb[0])
    return _rewrap(elem, wa, wb)


def _element_binary(op: str, a: FinType, b: FinType) -> FinType:
    if op in ("+", "-"):
        if isinstance(a, Money) and isinstance(b, Money):
            if a.currency != b.currency:
                raise CurrencyError(
                    f"cannot {op} different currencies {a.currency} and {b.currency} "
                    f"without an explicit fx_convert"
                )
            return a
        if isinstance(a, Days) and isinstance(b, Days):
            return Days()
        if isinstance(a, Percentage) and isinstance(b, Percentage):
            return Percentage()
        if isinstance(a, Ratio) and isinstance(b, Ratio):
            return Ratio()
        if isinstance(a, Scalar) and isinstance(b, Scalar):
            return Scalar()
        if isinstance(a, Quantity) and isinstance(b, Quantity):
            return a
        raise TypeCheckError(f"invalid operation: {a.textual()} {op} {b.textual()}")

    if op == "*":
        if isinstance(a, Money) and isinstance(b, (Percentage, Ratio, Scalar)):
            return a
        if isinstance(b, Money) and isinstance(a, (Percentage, Ratio, Scalar)):
            return b
        if isinstance(a, Quantity) and isinstance(b, Money):
            return b
        if isinstance(b, Quantity) and isinstance(a, Money):
            return a
        if isinstance(a, Days) and isinstance(b, (Scalar, Ratio, Percentage)):
            return Days()
        if isinstance(b, Days) and isinstance(a, (Scalar, Ratio, Percentage)):
            return Days()
        if isinstance(a, _NUMERIC_LIKE) and isinstance(b, _NUMERIC_LIKE):
            # percentage * scalar -> percentage, etc. Prefer the non-scalar side.
            if isinstance(a, Scalar):
                return b
            return a
        raise TypeCheckError(f"invalid operation: {a.textual()} * {b.textual()}")

    if op == "/":
        if isinstance(a, Money) and isinstance(b, Money):
            if a.currency != b.currency:
                raise CurrencyError(
                    f"cannot divide {a.currency} by {b.currency} without an explicit fx_convert"
                )
            return Ratio()
        if isinstance(a, Money) and isinstance(b, (Scalar, Quantity, Percentage, Ratio)):
            return a
        if isinstance(a, Money) and isinstance(b, Days):
            return Rate(per="day")
        if isinstance(a, Days) and isinstance(b, (Scalar, Ratio, Percentage)):
            return Days()
        if isinstance(a, Days) and isinstance(b, Days):
            return Ratio()
        if isinstance(a, _NUMERIC_LIKE) and isinstance(b, _NUMERIC_LIKE):
            if isinstance(a, Scalar) and isinstance(b, Scalar):
                return Scalar()
            return Ratio()
        if isinstance(a, Quantity) and isinstance(b, Quantity):
            return Scalar()
        raise TypeCheckError(f"invalid operation: {a.textual()} / {b.textual()}")

    raise TypeCheckError(f"unknown operator {op!r}")


def is_money(t: FinType) -> bool:
    el, _ = _unwrap(t)
    return isinstance(el, Money)


def currency_of(t: FinType) -> str | None:
    el, _ = _unwrap(t)
    return el.currency if isinstance(el, Money) else None
