"""Realized outcomes and traditional-detection markers for the feedback loop.

These objects close the loop between what EIF *predicted* and what actually
happened, and record when a *conventional* financial system would have flagged
the same event. The latter powers the Economic Signal Lead Time (ESLT) metric.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ..utils.ids import new_id
from .base import EIFModel, utcnow


class RealizedOutcome(EIFModel):
    """The observed real-world result for an event, recorded after the fact."""

    id: str = Field(default_factory=lambda: new_id("outcome"))
    event_id: str
    occurred: bool = Field(
        default=True, description="Whether the predicted event actually occurred."
    )
    realized_at: datetime | None = None
    recorded_at: datetime = Field(default_factory=utcnow)

    # Realized numeric outcomes keyed by metric, e.g. {"cost_of_goods_sold": 3_900_000}.
    realized_metrics: dict[str, float] = Field(default_factory=dict)
    currency: str | None = None
    note: str | None = None

    # When a conventional/structured financial indicator identified this event.
    # ESLT = traditional_detected_at - event.detected_at.
    traditional_detected_at: datetime | None = None
    traditional_source: str | None = None
