"""Shared base classes and small value objects for the domain model."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from ..version import SCHEMA_VERSION


def utcnow() -> datetime:
    """Timezone-aware current UTC time (used as a default factory)."""
    return datetime.now(UTC)


class EIFModel(BaseModel):
    """Base for all EIF domain objects.

    * Uses enum *values* on serialization so JSON is stable and provider-friendly.
    * Forbids unknown fields to catch schema drift early.
    * Validates on assignment so mutations stay well-typed.
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
        ser_json_timedelta="float",
    )

    schema_version: str = Field(default=SCHEMA_VERSION, description="Domain schema version.")


class Money(BaseModel):
    """A currency amount. Amount is a plain float for JSON friendliness.

    For deterministic arithmetic the impact engine works in float space and
    rounds at the boundary; monetary precision beyond cents is not claimed.
    """

    model_config = ConfigDict(extra="forbid")

    amount: float
    currency: str = Field(min_length=3, max_length=3, description="ISO-4217 code, e.g. ZAR.")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.amount:,.2f} {self.currency}"


class TimeWindow(BaseModel):
    """An optional [start, end] window with an optional duration in days."""

    model_config = ConfigDict(extra="forbid")

    start: datetime | None = None
    end: datetime | None = None
    duration_days: float | None = None
