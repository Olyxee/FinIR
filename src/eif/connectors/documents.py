"""Document connectors: PDF (and a placeholder for Word)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain import Evidence
from ..domain.enums import Modality, SourceType
from ..exceptions import ConnectorError
from .base import EIFConnector
from .text import _is_existing_file


class PdfConnector(EIFConnector):
    """Extracts text from ``.pdf`` files (requires optional ``pypdf``)."""

    modality = Modality.DOCUMENT
    source_type = SourceType.FILE

    def can_handle(self, source: Any) -> bool:
        return _is_existing_file(source, {".pdf"})

    def load(self, source: Any) -> list[Evidence]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ConnectorError(
                "Reading PDF files requires the optional 'pypdf' dependency. "
                "Install with: pip install 'economic-intelligence-framework[pdf]'"
            ) from exc
        path = Path(source)
        self.read_file_bytes(path)  # size/mime validation
        try:
            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:
            raise ConnectorError(f"Failed to read PDF {path}: {exc}") from exc
        text = "\n\n".join(f"[page {i + 1}]\n{p}" for i, p in enumerate(pages)).strip()
        if not text:
            text = "[no extractable text — document may be scanned; use a vision/OCR adapter]"
        return [
            self.make_text_evidence(
                text,
                source=path.name,
                modality=Modality.DOCUMENT,
                mime_type="application/pdf",
                metadata={"pages": str(len(pages))},
            )
        ]
