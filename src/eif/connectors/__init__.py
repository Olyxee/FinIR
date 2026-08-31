"""Multimodal connector framework.

Reference connectors turn files, payloads, and directories into the common
:class:`~eif.domain.Evidence` format. Integration connectors (email inbox, chat,
CRM, ERP, database, cloud storage) ship as documented interface placeholders.
"""

from __future__ import annotations

from .base import ConnectorContext, EIFConnector, guess_modality
from .directory import DirectoryConnector
from .documents import PdfConnector
from .media import AudioConnector, ImageConnector
from .placeholders import (
    ChatConnector,
    CloudStorageConnector,
    CrmConnector,
    DatabaseConnector,
    ErpConnector,
    InboxConnector,
)
from .registry import ConnectorRegistry, default_registry
from .structured import CsvConnector, ExcelConnector, JsonConnector
from .text import EmailConnector, TextConnector

__all__ = [
    "EIFConnector",
    "ConnectorContext",
    "ConnectorRegistry",
    "default_registry",
    "guess_modality",
    # reference connectors
    "TextConnector",
    "EmailConnector",
    "JsonConnector",
    "CsvConnector",
    "ExcelConnector",
    "PdfConnector",
    "AudioConnector",
    "ImageConnector",
    "DirectoryConnector",
    # integration placeholders
    "InboxConnector",
    "ChatConnector",
    "CrmConnector",
    "ErpConnector",
    "DatabaseConnector",
    "CloudStorageConnector",
]
