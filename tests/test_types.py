"""Finance-aware type system tests."""

from __future__ import annotations

import pytest

from finir.exceptions import CurrencyError, TypeCheckError
from finir.types import (
    Days,
    Money,
    Percentage,
    Ratio,
    Scalar,
    Series,
    binary_result,
    parse_type,
)


def test_parse_type_roundtrip():
    for text in ["money[ZAR]", "percentage", "ratio", "days", "scalar", "series[money[USD],month]"]:
        assert parse_type(text).textual() == text


def test_money_minus_money_same_currency():
    assert binary_result("-", Money("ZAR"), Money("ZAR")) == Money("ZAR")


def test_money_over_money_is_ratio():
    assert isinstance(binary_result("/", Money("ZAR"), Money("ZAR")), Ratio)


def test_money_times_percentage_is_money():
    assert binary_result("*", Money("ZAR"), Percentage()) == Money("ZAR")
    assert binary_result("*", Percentage(), Money("ZAR")) == Money("ZAR")


def test_currency_mismatch_add_raises():
    with pytest.raises(CurrencyError):
        binary_result("+", Money("USD"), Money("ZAR"))


def test_currency_mismatch_divide_raises():
    with pytest.raises(CurrencyError):
        binary_result("/", Money("USD"), Money("ZAR"))


def test_money_plus_days_invalid():
    with pytest.raises(TypeCheckError):
        binary_result("+", Money("ZAR"), Days())


def test_money_times_money_invalid():
    with pytest.raises(TypeCheckError):
        binary_result("*", Money("ZAR"), Money("ZAR"))


def test_series_wrapping_preserved():
    t = binary_result("-", Series(Money("ZAR"), "month"), Series(Money("ZAR"), "month"))
    assert isinstance(t, Series) and t.element == Money("ZAR")


def test_scalar_algebra():
    assert isinstance(binary_result("*", Scalar(), Scalar()), Scalar)
    assert isinstance(binary_result("/", Scalar(), Scalar()), Scalar)
