"""Evidence: raw or normalized information entering the system.

Evidence is the root of all provenance. Content may be inlined (``content``) for
small text/JSON payloads or referenced by path/URI (``content_ref``) for larger
binary artifacts. A ``content_hash`` is always computed so downstream conclusions
can be tied to an immutable snapshot of the source.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from ..utils.hashing import hash_text
from ..utils.ids import new_id
from .base import EIFModel, utcnow
from .enums import Modality, SourceType


class SecurityContext(EIFModel):
    """Access-control / tenancy metadata carried with each piece of evidence."""

    organization_id: str | None = None
    business_unit: str | None = None
    classification: str = Field(
        default="internal", description="e.g. public | internal | confidential | restricted."
    )
    access_tags: list[str] = Field(default_factory=list)
    contains_pii: bool = False


class Evidence(EIFModel):
    """A single unit of business evidence."""

    id: str = Field(default_factory=lambda: new_id("evidence"))
    source: str = Field(description="Human-readable origin, e.g. filename, email subject, table.")
    source_type: SourceType = SourceType.UNKNOWN
    modality: Modality = Modality.TEXT

    # When the underlying real-world artifact was created (e.g. email sent date),
    # which is what ESLT and effective-date reasoning care about. Distinct from
    # ``ingested_at`` (when EIF first saw it).
    created_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=utcnow)

    content: str | None = Field(default=None, description="Inlined text/JSON content, if small.")
    content_ref: str | None = Field(default=None, description="Path or URI to external content.")
    content_hash: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None

    security: SecurityContext = Field(default_factory=SecurityContext)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_content(self) -> Evidence:
        if self.content is None and self.content_ref is None:
            raise ValueError("Evidence requires either 'content' or 'content_ref'.")
        if self.content is not None and self.content_hash is None:
            self.content_hash = hash_text(self.content)
        return self

    @property
    def effective_time(self) -> datetime:
        """Best available timestamp for the underlying artifact."""
        return self.created_at or self.ingested_at

    def text(self) -> str:
        """Return inlined text content or raise if only an external ref exists."""
        if self.content is None:
            raise ValueError(
                f"Evidence {self.id} has no inlined content; load via connector/parser first."
            )
        return self.content
