"""Audio and image connectors backed by pluggable providers.

These wire the transcription/vision provider interfaces into the connector SDK.
With the default deterministic mock providers they run fully offline; swap in a
real :class:`TranscriptionProvider` / :class:`VisionProvider` for production.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..domain import Evidence
from ..domain.enums import Modality, SourceType
from ..providers.base import TranscriptionProvider, VisionProvider
from ..providers.mock import MockTranscriptionProvider, MockVisionProvider
from .base import ConnectorContext, EIFConnector
from .text import _is_existing_file

_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".txt"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


class AudioConnector(EIFConnector):
    """Transcribes audio files into transcript Evidence via a TranscriptionProvider."""

    modality = Modality.TRANSCRIPT
    source_type = SourceType.FILE

    def __init__(
        self,
        context: ConnectorContext | None = None,
        *,
        provider: TranscriptionProvider | None = None,
    ) -> None:
        super().__init__(context)
        self.provider = provider or MockTranscriptionProvider()
        # Audio bytes bypass the text/* MIME allow-list; widen it locally.
        self.context.security.allowed_mime_prefixes = [
            *self.context.security.allowed_mime_prefixes,
            "audio/",
        ]

    def can_handle(self, source: Any) -> bool:
        return _is_existing_file(source, _AUDIO_SUFFIXES)

    def load(self, source: Any) -> list[Evidence]:
        path = Path(source)
        audio = self.read_file_bytes(path)
        transcript = self.provider.transcribe(audio)
        return [
            self.make_text_evidence(
                transcript,
                source=path.name,
                modality=Modality.TRANSCRIPT,
                mime_type="text/plain",
                metadata={"transcription_model": self.provider.model},
            )
        ]


class ImageConnector(EIFConnector):
    """Describes images into Evidence via a VisionProvider."""

    modality = Modality.IMAGE
    source_type = SourceType.FILE

    def __init__(
        self,
        context: ConnectorContext | None = None,
        *,
        provider: VisionProvider | None = None,
    ) -> None:
        super().__init__(context)
        self.provider = provider or MockVisionProvider()
        self.context.security.allowed_mime_prefixes = [
            *self.context.security.allowed_mime_prefixes,
            "image/",
        ]

    def can_handle(self, source: Any) -> bool:
        return _is_existing_file(source, _IMAGE_SUFFIXES)

    def load(self, source: Any) -> list[Evidence]:
        path = Path(source)
        image = self.read_file_bytes(path)
        observation = self.provider.describe_image(image)
        return [
            self.make_text_evidence(
                observation.description,
                source=path.name,
                modality=Modality.IMAGE,
                mime_type="text/plain",
                metadata={
                    "vision_model": self.provider.model,
                    "tags": ",".join(observation.tags),
                },
            )
        ]
