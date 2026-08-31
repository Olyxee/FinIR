"""Identifier helpers.

EIF uses two kinds of identifiers:

* **Random ids** (``new_id``) for freshly created objects — UUID4 hex, prefixed
  with a short type tag so that ids are self-describing in logs (e.g. ``ev_1a2b``).
* **Deterministic ids** (``deterministic_id``) derived from stable content, used
  where reproducibility matters (benchmark fixtures, entity keys, dedup). Same
  inputs always yield the same id, which keeps tests and benchmarks stable.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable

# Short, human-recognizable prefixes per object type.
PREFIXES = {
    "evidence": "ev",
    "observation": "ob",
    "entity": "en",
    "event": "evt",
    "impact": "imp",
    "relationship": "rel",
    "outcome": "out",
    "run": "run",
    "provenance": "prov",
}


def new_id(kind: str) -> str:
    """Return a fresh random id for ``kind`` (e.g. ``evt_9f3c1a2b``)."""
    prefix = PREFIXES.get(kind, kind[:3])
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def deterministic_id(kind: str, *parts: object) -> str:
    """Return a stable id derived from ``parts``.

    Useful for entity keys and benchmark fixtures where the same logical object
    must always receive the same id across runs and machines.
    """
    prefix = PREFIXES.get(kind, kind[:3])
    joined = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def entity_key(entity_type: str, name: str, *extra: object) -> str:
    """Normalize an entity into a stable dedup key (case/space-insensitive)."""
    normalized = " ".join(str(name).lower().split())
    return deterministic_id("entity", entity_type, normalized, *extra)


def stable_hash(parts: Iterable[object]) -> str:
    """Return a full sha256 hex digest over ``parts`` (order-sensitive)."""
    joined = "|".join(str(p) for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
