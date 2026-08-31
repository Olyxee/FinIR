"""The optional natural-language intent layer.

Core FinIR consumes the *structured* canonical intent (see :mod:`finir.intent.schema`).
An :class:`IntentCompiler` turns natural language into that canonical envelope. This
is the seam the Hugging Face workstream replaces with a trained model — it must emit
exactly the contract in :mod:`finir.intent.schema`.

A dependency-free :class:`MockIntentCompiler` is provided so examples and tests run
offline. It demonstrates the *contract*, including the non-executable statuses
(ambiguous / unsupported) — it is not a language model.
"""

from __future__ import annotations

import abc
import re
from typing import Any

from .schema import SCHEMA_VERSION

_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_UP_WORDS = ("increase", "raise", "grow", "rise", "up", "higher")
_DOWN_WORDS = ("decrease", "reduce", "cut", "lower", "drop", "down", "fall")
# Requests that are clear but cannot be expressed as a FinIR model mutation.
_UNSUPPORTED_WORDS = (
    "acquire",
    "acquisition",
    "merge",
    "merger",
    "hire",
    "fire ",
    "lay off",
    "layoff",
    "ipo",
    "buy back",
    "buyback",
    "litigation",
    "sue",
)
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


class IntentCompiler(abc.ABC):
    """Turns a natural-language request into a canonical FinIR intent envelope."""

    @abc.abstractmethod
    def compile(self, text: str) -> dict[str, Any]:
        """Return a canonical intent envelope (see finir-intent-v1.schema.json)."""


class MockIntentCompiler(IntentCompiler):
    """A deterministic, offline pattern-based intent compiler (no LLM).

    Emits the canonical envelope, including ``ambiguous`` and ``unsupported`` statuses
    for non-quantified or non-representable requests — the behaviour a real model must
    also implement so vague language never becomes invented numbers.
    """

    def __init__(self, metric_aliases: dict[str, str] | None = None) -> None:
        # Note: these NL aliases live in the *interpretation* layer, not the contract.
        # The canonical target is a model input node name; FinIR resolves no aliases.
        self.metric_aliases = {**_METRIC_WORDS, **(metric_aliases or {})}

    def compile(self, text: str) -> dict[str, Any]:
        low = text.lower()

        if any(w in low for w in _UNSUPPORTED_WORDS):
            return _envelope(
                "unsupported",
                reason=f"request cannot be represented as a FinIR model mutation: {text!r}",
            )

        target = self._find_metric(low)
        if target is None:
            return _envelope("ambiguous", reason="no financial target metric was identified")

        # payment terms "30 to 60 days" -> set 60
        term = re.search(r"(\d+)\s*(?:to|->|→)\s*(\d+)\s*day", low)
        if term and target == "payment_terms":
            return _envelope(
                "valid",
                operations=[
                    {
                        "operation": "set",
                        "target": target,
                        "value": float(term.group(2)),
                        "unit": "days",
                    }
                ],
            )

        m = _PCT_RE.search(low)
        if m:
            up = any(w in low for w in _UP_WORDS)
            down = any(w in low for w in _DOWN_WORDS)
            sign = -1.0 if (down and not up) else 1.0
            return _envelope(
                "valid",
                operations=[
                    {
                        "operation": "relative_change",
                        "target": target,
                        "value": sign * float(m.group(1)) / 100.0,
                    }
                ],
            )

        # A metric was named but no quantity was given -> not executable.
        return _envelope(
            "ambiguous",
            reason=f"a target ({target}) was identified but no quantitative change was specified",
        )

    def _find_metric(self, low: str) -> str | None:
        for alias in sorted(self.metric_aliases, key=len, reverse=True):
            if alias in low:
                return self.metric_aliases[alias]
        return None


def _envelope(
    status: str, *, operations: list[dict[str, Any]] | None = None, reason: str | None = None
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "operations": operations or [],
    }
    if reason is not None:
        env["reason"] = reason
    return env
