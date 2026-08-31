"""Lightweight, dependency-free PII redaction hooks.

This is intentionally conservative and regex-based. It is *not* a substitute for a
dedicated PII engine, but provides a safe default and a clean extension point:
callers can register additional :class:`RedactionRule` objects, and connectors
apply :func:`redact` to evidence content when ``redact_pii`` is enabled.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionRule:
    """A named regex rule that replaces matches with a placeholder token."""

    name: str
    pattern: re.Pattern[str]
    replacement: str


# Ordered so that more specific patterns run first.
DEFAULT_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        "email",
        re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
        "[REDACTED_EMAIL]",
    ),
    RedactionRule(
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
        "[REDACTED_IBAN]",
    ),
    RedactionRule(
        "credit_card",
        re.compile(r"\b(?:\d[ -]?){13,16}\b"),
        "[REDACTED_CARD]",
    ),
    RedactionRule(
        "phone",
        re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)"),
        "[REDACTED_PHONE]",
    ),
)


def redact(text: str, *, rules: Iterable[RedactionRule] | None = None) -> str:
    """Return ``text`` with matches of each rule replaced by its placeholder."""
    active = tuple(rules) if rules is not None else DEFAULT_RULES
    out = text
    for rule in active:
        out = rule.pattern.sub(rule.replacement, out)
    return out


def redaction_report(text: str, *, rules: Iterable[RedactionRule] | None = None) -> dict[str, int]:
    """Return a count of matches per rule without modifying ``text``.

    Useful for audit logs: record *that* PII was present and how much, without
    storing the PII itself.
    """
    active = tuple(rules) if rules is not None else DEFAULT_RULES
    return {rule.name: len(rule.pattern.findall(text)) for rule in active}
