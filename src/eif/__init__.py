"""Economic Intelligence Framework (EIF).

Open infrastructure for converting multimodal business evidence into standardized,
machine-readable economic events and estimated financial consequences::

    Business Evidence -> Observations -> Economic Events -> Financial Consequences

The high-level entry point is :class:`eif.facade.EIF`. Core domain objects are
re-exported here for convenience.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .domain import (
    Confidence,
    EconomicEntity,
    EconomicEvent,
    EconomicImpact,
    Estimate,
    Evidence,
    Observation,
    Provenance,
    RealizedOutcome,
)
from .version import __version__

if TYPE_CHECKING:
    from .facade import EIF, AnalysisResult


def __getattr__(name: str) -> object:
    # Lazily expose the facade so `import eif` stays cheap and free of optional
    # backend imports until the user actually constructs an EIF instance.
    if name in ("EIF", "AnalysisResult"):
        from . import facade

        return getattr(facade, name)
    raise AttributeError(f"module 'eif' has no attribute {name!r}")


__all__ = [
    "EIF",
    "AnalysisResult",
    "Confidence",
    "EconomicEntity",
    "EconomicEvent",
    "EconomicImpact",
    "Estimate",
    "Evidence",
    "Observation",
    "Provenance",
    "RealizedOutcome",
    "__version__",
]
