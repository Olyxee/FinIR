"""Directory / multi-file ingestion connector."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..domain import Evidence
from ..domain.enums import Modality, SourceType
from .base import ConnectorContext, EIFConnector
from .text import _is_existing_file

if TYPE_CHECKING:
    from .registry import ConnectorRegistry

# Extensions the directory connector will attempt to ingest.
_INGESTIBLE = {
    ".txt",
    ".md",
    ".log",
    ".eml",
    ".json",
    ".csv",
    ".tsv",
    ".xlsx",
    ".xlsm",
    ".pdf",
}


class DirectoryConnector(EIFConnector):
    """Recursively ingests supported files in a directory via a registry."""

    modality = Modality.TEXT
    source_type = SourceType.FILE

    def __init__(
        self,
        context: ConnectorContext | None = None,
        *,
        registry: ConnectorRegistry | None = None,
        recursive: bool = True,
    ) -> None:
        super().__init__(context)
        self._registry = registry
        self.recursive = recursive

    def bind_registry(self, registry: ConnectorRegistry) -> None:
        self._registry = registry

    def can_handle(self, source: Any) -> bool:
        return isinstance(source, str | Path) and Path(source).is_dir()

    def load(self, source: Any) -> list[Evidence]:
        if self._registry is None:
            raise RuntimeError("DirectoryConnector requires a bound ConnectorRegistry.")
        root = Path(source)
        pattern = "**/*" if self.recursive else "*"
        evidence: list[Evidence] = []
        for path in sorted(root.glob(pattern)):
            if (
                path.is_file()
                and path.suffix.lower() in _INGESTIBLE
                and not path.name.startswith(".")
            ):
                evidence.extend(self._registry.load(path))
        return evidence


def is_ingestible_file(source: Any) -> bool:
    return _is_existing_file(source, _INGESTIBLE)
