"""Connector registry and dispatcher.

The registry holds an ordered list of connector instances and routes each source
to the first connector whose ``can_handle`` returns True. This is what turns a
heterogeneous list of inputs — file paths, directories, raw strings, dicts — into
a flat list of :class:`Evidence`.
"""

from __future__ import annotations

from typing import Any

from ..domain import Evidence
from ..exceptions import UnsupportedModalityError
from .base import ConnectorContext, EIFConnector
from .directory import DirectoryConnector
from .documents import PdfConnector
from .media import AudioConnector, ImageConnector
from .structured import CsvConnector, ExcelConnector, JsonConnector
from .text import EmailConnector, TextConnector


class ConnectorRegistry:
    """Ordered collection of connectors with first-match dispatch."""

    def __init__(self, connectors: list[EIFConnector] | None = None) -> None:
        self._connectors: list[EIFConnector] = connectors or []

    def register(self, connector: EIFConnector, *, first: bool = False) -> None:
        if first:
            self._connectors.insert(0, connector)
        else:
            self._connectors.append(connector)

    @property
    def connectors(self) -> list[EIFConnector]:
        return list(self._connectors)

    def find(self, source: Any) -> EIFConnector | None:
        for connector in self._connectors:
            if connector.can_handle(source):
                return connector
        return None

    def load(self, source: Any) -> list[Evidence]:
        connector = self.find(source)
        if connector is None:
            raise UnsupportedModalityError(
                f"No connector can handle source: {source!r}. "
                "Register a custom EIFConnector or convert the source first."
            )
        return connector.load(source)

    def load_many(self, sources: list[Any]) -> list[Evidence]:
        evidence: list[Evidence] = []
        for source in sources:
            evidence.extend(self.load(source))
        return evidence


def default_registry(context: ConnectorContext | None = None) -> ConnectorRegistry:
    """Build a registry with all reference connectors, ordered specific-first."""
    ctx = context or ConnectorContext()
    directory = DirectoryConnector(ctx)
    registry = ConnectorRegistry(
        [
            directory,
            EmailConnector(ctx),
            JsonConnector(ctx),
            CsvConnector(ctx),
            ExcelConnector(ctx),
            PdfConnector(ctx),
            AudioConnector(ctx),
            ImageConnector(ctx),
            # TextConnector is last: it is the permissive fallback for raw strings
            # and plain-text files.
            TextConnector(ctx),
        ]
    )
    directory.bind_registry(registry)
    return registry
