"""Optional natural-language intent layer (item 9).

Core FinIR consumes *structured* financial intent. Natural-language interpretation
is deliberately a thin, optional layer on top: an :class:`IntentCompiler` turns a
question into a structured intent dict that :meth:`FinancialModel.apply_intent`
executes. The model interprets; the runtime computes.

A dependency-free :class:`MockIntentCompiler` is provided so examples and tests run
offline. Real LLM-backed compilers can implement the same interface behind extras.
"""

from __future__ import annotations

import abc
import re
from typing import Any

from .exceptions import FinIRError


class IntentCompiler(abc.ABC):
    """Turns a natural-language request into a structured financial intent."""

    @abc.abstractmethod
    def compile(self, text: str) -> dict[str, Any]: ...


_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_UP_WORDS = ("increase", "raise", "grow", "rise", "up", "higher")
_DOWN_WORDS = ("decrease", "reduce", "cut", "lower", "drop", "down", "fall")
_METRIC_WORDS = {
    "cogs": "cogs",
    "cost of goods": "cogs",
    "supplier cost": "cogs",
    "supplier costs": "cogs",
    "revenue": "revenue",
    "sales": "revenue",
    "opex": "opex",
    "operating expenses": "opex",
    "price": "price",
    "payment terms": "payment_terms",
}


class MockIntentCompiler(IntentCompiler):
    """A deterministic, offline pattern-based intent compiler (no LLM).

    Handles the common phrasings used in examples/tests. It is intentionally simple
    — its job is to demonstrate the *interface*, not to be a language model.
    """

    def __init__(self, metric_aliases: dict[str, str] | None = None) -> None:
        self.metric_aliases = {**_METRIC_WORDS, **(metric_aliases or {})}

    def compile(self, text: str) -> dict[str, Any]:
        low = text.lower()
        target = self._find_metric(low)
        if target is None:
            raise FinIRError(f"could not identify a target metric in: {text!r}")

        # payment terms "30 to 60 days" -> absolute set 60
        term = re.search(r"(\d+)\s*(?:to|->|→)\s*(\d+)\s*day", low)
        if term and target == "payment_terms":
            return {"operation": "set", "target": target, "value": float(term.group(2))}

        m = _PCT_RE.search(low)
        if m:
            up = any(w in low for w in _UP_WORDS)
            down = any(w in low for w in _DOWN_WORDS)
            sign = -1.0 if (down and not up) else 1.0
            return {
                "operation": "relative_change",
                "target": target,
                "value": sign * float(m.group(1)) / 100.0,
            }
        raise FinIRError(f"could not parse a change from: {text!r}")

    def _find_metric(self, low: str) -> str | None:
        # longest alias first so "supplier cost" beats "cost"
        for alias in sorted(self.metric_aliases, key=len, reverse=True):
            if alias in low:
                return self.metric_aliases[alias]
        return None
