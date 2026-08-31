"""Deterministic, fully-local mock providers.

These are the default providers. They never touch the network, produce identical
output for identical input, and let the entire framework — pipeline, CLI, API,
benchmark — run and be tested without any API keys. They are *not* meant to be
accurate models; they are meant to be reproducible and dependency-free.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .base import (
    EmbeddingProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenUsage,
    TranscriptionProvider,
    VisionObservation,
    VisionProvider,
)


def _seed_from(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


class MockLLMProvider(LLMProvider):
    """A deterministic LLM stand-in.

    * If a ``json_schema`` is requested, returns a stable JSON object populated
      with neutral defaults for the schema's top-level properties.
    * Otherwise returns a short deterministic acknowledgement that echoes a hash
      of the prompt, so callers can assert reproducibility.
    """

    name = "mock"

    def __init__(self, model: str = "mock-llm-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def sends_data_offhost(self) -> bool:
        return False

    def generate(self, request: LLMRequest) -> LLMResponse:
        prompt = "\n".join(m.content for m in request.messages)
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]

        if request.json_schema is not None:
            text = json.dumps(_fill_schema(request.json_schema, prompt), sort_keys=True)
        else:
            text = f"[mock:{self._model}] deterministic response to prompt#{digest}"

        usage = TokenUsage(
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_tokens=len(prompt.split()) + len(text.split()),
        )
        return LLMResponse(text=text, model=self._model, provider=self.name, usage=usage)


def _fill_schema(schema: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Produce a deterministic object matching the top-level schema properties."""
    props = schema.get("properties", {})
    out: dict[str, Any] = {}
    for key, spec in props.items():
        typ = spec.get("type", "string")
        if typ == "number" or typ == "integer":
            out[key] = float(_seed_from(prompt + key) % 100)
        elif typ == "boolean":
            out[key] = bool(_seed_from(prompt + key) % 2)
        elif typ == "array":
            out[key] = []
        elif typ == "object":
            out[key] = {}
        else:
            out[key] = f"mock:{key}"
    return out


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embeddings (local, no network)."""

    name = "mock"

    def __init__(self, model: str = "mock-embed-v1", dim: int = 64) -> None:
        self._model = model
        self._dim = dim

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dim

    @property
    def sends_data_offhost(self) -> bool:
        return False

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vectors.append(self._embed_one(text))
        return vectors

    def _embed_one(self, text: str) -> list[float]:
        # Deterministic pseudo-random unit vector from repeated hashing.
        vals: list[float] = []
        block = text.encode("utf-8")
        while len(vals) < self._dim:
            block = hashlib.sha256(block).digest()
            for b in block:
                vals.append((b / 255.0) * 2.0 - 1.0)
                if len(vals) >= self._dim:
                    break
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


class MockVisionProvider(VisionProvider):
    """Deterministic vision stand-in that summarizes image bytes."""

    name = "mock"

    def __init__(self, model: str = "mock-vision-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def sends_data_offhost(self) -> bool:
        return False

    def describe_image(self, image: bytes, *, prompt: str | None = None) -> VisionObservation:
        digest = hashlib.sha256(image).hexdigest()[:8]
        return VisionObservation(
            description=f"[mock-vision] image#{digest} ({len(image)} bytes)",
            tags=["mock"],
            confidence=0.3,
        )


class MockTranscriptionProvider(TranscriptionProvider):
    """Deterministic transcription stand-in.

    For testing convenience, if the audio bytes are valid UTF-8 text they are
    returned verbatim (so a ``.txt`` can masquerade as a transcript in fixtures);
    otherwise a deterministic placeholder is returned.
    """

    name = "mock"

    def __init__(self, model: str = "mock-transcribe-v1") -> None:
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def sends_data_offhost(self) -> bool:
        return False

    def transcribe(self, audio: bytes, *, language: str | None = None) -> str:
        try:
            return audio.decode("utf-8")
        except UnicodeDecodeError:
            digest = hashlib.sha256(audio).hexdigest()[:8]
            return f"[mock-transcript] audio#{digest} ({len(audio)} bytes)"
