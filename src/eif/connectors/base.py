"""Connector SDK.

A connector turns some external source (a file, a payload, a directory, an
inbox) into one or more :class:`Evidence` objects in the common format. Implement
one by subclassing :class:`EIFConnector`::

    class MyConnector(EIFConnector):
        modality = Modality.API
        def can_handle(self, source): ...
        def load(self, source): ...

Connectors must not require live third-party credentials to be imported, and the
built-in reference connectors run entirely offline. Security controls (file-size
limit, MIME allow-list, safe path handling, optional PII redaction) live here so
every connector inherits them via :func:`make_evidence` / :func:`read_file_bytes`.
"""

from __future__ import annotations

import abc
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import SecurityConfig
from ..domain import Evidence, SecurityContext
from ..domain.enums import Modality, SourceType
from ..exceptions import SecurityError, UnsupportedModalityError
from ..utils.hashing import hash_bytes, hash_text
from ..utils.redaction import redact, redaction_report


class ConnectorContext:
    """Shared settings passed to connectors (security + tenancy + redaction)."""

    def __init__(
        self,
        *,
        organization_id: str | None = None,
        business_unit: str | None = None,
        security: SecurityConfig | None = None,
    ) -> None:
        self.organization_id = organization_id
        self.business_unit = business_unit
        self.security = security or SecurityConfig()


class EIFConnector(abc.ABC):
    """Base class for all connectors."""

    modality: Modality = Modality.TEXT
    source_type: SourceType = SourceType.FILE

    def __init__(self, context: ConnectorContext | None = None) -> None:
        self.context = context or ConnectorContext()

    @abc.abstractmethod
    def can_handle(self, source: Any) -> bool:
        """Return True if this connector can load ``source``."""

    @abc.abstractmethod
    def load(self, source: Any) -> list[Evidence]:
        """Load ``source`` into one or more Evidence objects."""

    # -- helpers shared by subclasses ---------------------------------------
    def make_text_evidence(
        self,
        content: str,
        *,
        source: str,
        modality: Modality | None = None,
        created_at: datetime | None = None,
        metadata: dict[str, str] | None = None,
        mime_type: str | None = None,
    ) -> Evidence:
        """Build a text Evidence object with hashing, redaction, and tenancy."""
        sec = self.context.security
        contains_pii = False
        if sec.redact_pii:
            report = redaction_report(content)
            contains_pii = any(v > 0 for v in report.values())
            content = redact(content)
        size = len(content.encode("utf-8"))
        _enforce_size(size, sec.max_file_bytes)
        return Evidence(
            source=source,
            source_type=self.source_type,
            modality=modality or self.modality,
            created_at=created_at,
            content=content,
            content_hash=hash_text(content),
            mime_type=mime_type or "text/plain",
            size_bytes=size,
            metadata=metadata or {},
            security=SecurityContext(
                organization_id=self.context.organization_id,
                business_unit=self.context.business_unit,
                contains_pii=contains_pii,
            ),
        )

    def read_file_bytes(self, path: Path) -> bytes:
        """Read a file with size + MIME validation and safe handling."""
        path = Path(path)
        if not path.is_file():
            raise UnsupportedModalityError(f"Not a readable file: {path}")
        size = path.stat().st_size
        _enforce_size(size, self.context.security.max_file_bytes)
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        _enforce_mime(mime, self.context.security.allowed_mime_prefixes)
        return path.read_bytes()


def _enforce_size(size: int, max_bytes: int) -> None:
    if size > max_bytes:
        raise SecurityError(f"Evidence exceeds max size: {size} bytes > limit {max_bytes} bytes.")


def _enforce_mime(mime: str, allowed_prefixes: list[str]) -> None:
    if not any(mime.startswith(prefix) for prefix in allowed_prefixes):
        raise SecurityError(f"MIME type '{mime}' is not in the allow-list {allowed_prefixes}.")


def guess_modality(path: Path) -> Modality:
    """Best-effort modality inference from a file extension."""
    suffix = path.suffix.lower()
    return {
        ".txt": Modality.TEXT,
        ".md": Modality.TEXT,
        ".log": Modality.TEXT,
        ".eml": Modality.EMAIL,
        ".json": Modality.JSON,
        ".csv": Modality.TABLE,
        ".tsv": Modality.TABLE,
        ".xlsx": Modality.TABLE,
        ".xls": Modality.TABLE,
        ".pdf": Modality.DOCUMENT,
    }.get(suffix, Modality.TEXT)


def utcnow() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "ConnectorContext",
    "EIFConnector",
    "guess_modality",
    "hash_bytes",
]
