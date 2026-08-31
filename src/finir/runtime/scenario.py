"""Scenario change specifications and resolution (items 8, 12).

A *change spec* expresses how an input moves, in a form an AI agent or a human can
write compactly:

    "+8%"        relative increase          -> current * 1.08
    "-8%"        relative decrease          -> current * 0.92
    "30d->60d"   absolute retarget          -> 60
    500_000      absolute set               -> 500000
    {"relative": 0.04}                       -> current * 1.04
    {"absolute": 60}                         -> 60
    {"delta": 5}                             -> current + 5
"""

from __future__ import annotations

import re
from typing import Any

from ..exceptions import FinIRError

_REL_RE = re.compile(r"^([+-])\s*(\d+(?:\.\d+)?)\s*%$")
_ARROW_RE = re.compile(r"^\s*[\d.]+\s*[a-zA-Z]*\s*->\s*(\d+(?:\.\d+)?)\s*[a-zA-Z]*\s*$")
_NUM_UNIT_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*[a-zA-Z%]*\s*$")


def resolve_change(current: float | None, spec: Any) -> float:
    """Resolve a change spec against the current value into a concrete new value."""
    cur = 0.0 if current is None else float(current)
    if isinstance(spec, (int, float)):
        return float(spec)
    if isinstance(spec, dict):
        if "relative" in spec:
            return cur * (1.0 + float(spec["relative"]))
        if "delta" in spec:
            return cur + float(spec["delta"])
        if "absolute" in spec:
            return float(spec["absolute"])
        raise FinIRError(f"unrecognized change spec {spec!r}")
    if isinstance(spec, str):
        s = spec.strip()
        m = _REL_RE.match(s)
        if m:
            pct = float(m.group(2)) / 100.0
            return cur * (1.0 + pct) if m.group(1) == "+" else cur * (1.0 - pct)
        m = _ARROW_RE.match(s)
        if m:
            return float(m.group(1))
        m = _NUM_UNIT_RE.match(s)
        if m:
            return float(m.group(1))
    raise FinIRError(f"could not parse change spec {spec!r}")
