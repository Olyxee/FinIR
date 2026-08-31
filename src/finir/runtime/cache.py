"""The finance-aware computation cache (item 11).

Cache keys bind a node to the *versions of the inputs it transitively depends on*
(plus scenario and model version). A node is reused only when every input feeding
it is unchanged — so a cached value can never leak across a changed input, while an
unaffected node is reused even under a different scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# A cache key: (node_name, signature) where signature is a hashable tuple of
# (input_name, input_version) pairs for the node's transitive inputs.
CacheKey = tuple[str, tuple]


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    recomputed: int = 0
    reused: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "recomputed": self.recomputed,
            "reused": self.reused,
            "hit_ratio": round(self.hit_ratio, 4),
        }


class ComputationCache:
    """A keyed value cache with hit/miss/reuse accounting."""

    def __init__(self) -> None:
        self._store: dict[CacheKey, Any] = {}
        self.stats = CacheStats()

    def get(self, key: CacheKey) -> Any:
        if key in self._store:
            self.stats.hits += 1
            self.stats.reused += 1
            return self._store[key]
        self.stats.misses += 1
        return None

    def put(self, key: CacheKey, value: Any) -> None:
        self._store[key] = value
        self.stats.recomputed += 1

    def contains(self, key: CacheKey) -> bool:
        return key in self._store

    def clear(self) -> None:
        self._store.clear()

    def reset_stats(self) -> None:
        self.stats = CacheStats()

    def __len__(self) -> int:
        return len(self._store)
