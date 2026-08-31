"""Request/response schemas for the EIF API."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class EvidenceIn(BaseModel):
    """Inline evidence submission."""

    source: str = "api-submission"
    content: str
    modality: str = "text"
    created_at: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    """Analyze a batch of inline text and/or JSON items."""

    texts: list[str] = Field(default_factory=list)
    json_items: list[dict[str, Any]] = Field(default_factory=list)


class OutcomeIn(BaseModel):
    event_id: str
    occurred: bool = True
    realized_at: str | None = None
    realized_metrics: dict[str, float] = Field(default_factory=dict)
    currency: str | None = None
    traditional_detected_at: str | None = None
    traditional_source: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool


class ErrorResponse(BaseModel):
    error: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
