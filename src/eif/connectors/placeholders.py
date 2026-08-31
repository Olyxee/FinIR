"""Documented interface placeholders for live integrations.

EIF ships *clean interfaces* — not fake implementations — for integrations that
require live third-party credentials (email inboxes, chat, CRM, ERP, databases,
cloud storage). Each raises a clear ``NotImplementedError`` describing exactly
what a real subclass must implement. This keeps the framework installable and
testable offline while giving integrators an obvious, typed extension point.

Example of implementing one::

    class SalesforceConnector(CrmConnector):
        def can_handle(self, source): return isinstance(source, SalesforceQuery)
        def load(self, source):
            records = self._client.query(source.soql)
            return [self.make_text_evidence(r.render(), source="salesforce", ...)
                    for r in records]
"""

from __future__ import annotations

from typing import Any

from ..domain import Evidence
from ..domain.enums import Modality, SourceType
from .base import EIFConnector


class _NotImplementedConnector(EIFConnector):
    integration_name: str = "integration"
    setup_hint: str = "Subclass this connector and implement can_handle()/load()."

    def can_handle(self, source: Any) -> bool:
        return False

    def load(self, source: Any) -> list[Evidence]:
        raise NotImplementedError(
            f"The {self.integration_name} connector is an interface placeholder. {self.setup_hint}"
        )


class InboxConnector(_NotImplementedConnector):
    """Live email inbox (IMAP/Graph/Gmail API). Use EmailConnector for .eml files."""

    integration_name = "email inbox"
    source_type = SourceType.EMAIL
    modality = Modality.EMAIL


class ChatConnector(_NotImplementedConnector):
    """Slack / Microsoft Teams message ingestion."""

    integration_name = "chat (Slack/Teams)"
    source_type = SourceType.CHAT
    modality = Modality.TEXT


class CrmConnector(_NotImplementedConnector):
    """CRM systems (Salesforce, HubSpot, ...)."""

    integration_name = "CRM"
    source_type = SourceType.CRM
    modality = Modality.JSON


class ErpConnector(_NotImplementedConnector):
    """ERP systems (SAP, NetSuite, ...)."""

    integration_name = "ERP"
    source_type = SourceType.ERP
    modality = Modality.JSON


class DatabaseConnector(_NotImplementedConnector):
    """Arbitrary SQL/NoSQL databases (bring your own query + driver)."""

    integration_name = "database"
    source_type = SourceType.DATABASE
    modality = Modality.TABLE


class CloudStorageConnector(_NotImplementedConnector):
    """Cloud object storage (S3, GCS, Azure Blob)."""

    integration_name = "cloud storage"
    source_type = SourceType.FILE
    modality = Modality.DOCUMENT
