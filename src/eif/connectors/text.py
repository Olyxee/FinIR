"""Text and email connectors."""

from __future__ import annotations

from email import message_from_bytes
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from ..domain import Evidence
from ..domain.enums import Modality, SourceType
from .base import EIFConnector

_TEXT_SUFFIXES = {".txt", ".md", ".log", ".text"}


def _is_existing_file(source: Any, suffixes: set[str]) -> bool:
    if not isinstance(source, str | Path):
        return False
    p = Path(source)
    try:
        return p.is_file() and p.suffix.lower() in suffixes
    except OSError:
        return False


class TextConnector(EIFConnector):
    """Loads plain-text files and raw in-memory strings."""

    modality = Modality.TEXT
    source_type = SourceType.FILE

    def can_handle(self, source: Any) -> bool:
        if _is_existing_file(source, _TEXT_SUFFIXES):
            return True
        # A raw string that is not a path to some other on-disk file.
        if isinstance(source, str):
            p = Path(source)
            try:
                is_other_file = p.is_file() and p.suffix.lower() not in _TEXT_SUFFIXES
            except OSError:
                is_other_file = False
            return not is_other_file
        return False

    def load(self, source: Any) -> list[Evidence]:
        if _is_existing_file(source, _TEXT_SUFFIXES):
            path = Path(source)
            data = self.read_file_bytes(path)
            text = data.decode("utf-8", errors="replace")
            return [
                self.make_text_evidence(
                    text, source=path.name, modality=Modality.TEXT, mime_type="text/plain"
                )
            ]
        # Raw string content.
        text = str(source)
        return [
            self.make_text_evidence(
                text, source="inline-text", modality=Modality.TEXT, mime_type="text/plain"
            )
        ]


class EmailConnector(EIFConnector):
    """Loads RFC-822 ``.eml`` files, extracting headers + body text."""

    modality = Modality.EMAIL
    source_type = SourceType.EMAIL

    def can_handle(self, source: Any) -> bool:
        return _is_existing_file(source, {".eml"})

    def load(self, source: Any) -> list[Evidence]:
        path = Path(source)
        raw = self.read_file_bytes(path)
        msg = message_from_bytes(raw)

        subject = str(msg.get("Subject", "")).strip()
        sender = str(msg.get("From", "")).strip()
        date_hdr = msg.get("Date")
        created_at = None
        if date_hdr:
            try:
                created_at = parsedate_to_datetime(date_hdr)
            except (TypeError, ValueError):
                created_at = None

        body = self._extract_body(msg)
        content = f"From: {sender}\nSubject: {subject}\n\n{body}".strip()
        return [
            self.make_text_evidence(
                content,
                source=subject or path.name,
                modality=Modality.EMAIL,
                created_at=created_at,
                mime_type="message/rfc822",
                metadata={"from": sender, "subject": subject},
            )
        ]

    @staticmethod
    def _extract_body(msg: Any) -> str:
        if msg.is_multipart():
            parts: list[str] = []
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        parts.append(payload.decode(charset, errors="replace"))
            return "\n".join(parts)
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return str(msg.get_payload())
