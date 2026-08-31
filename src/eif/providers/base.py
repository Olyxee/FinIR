"""Provider abstractions.

EIF is model-agnostic. It talks to four kinds of providers through narrow
interfaces so that any backend — OpenAI-compatible, Anthropic, Gemini, a local
endpoint, or a deterministic mock — can be swapped in without touching the
pipeline. Providers are *capabilities*, not god-objects: a backend implements
only the interfaces it supports.

Key design choice: the pipeline never trusts a model to do arithmetic or to be
the sole source of truth. LLMs are used for interpretation (classification,
applicability, assumptions), and their output is always validated against typed
schemas before use.
"""

from __future__ import annotations

import abc
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(description="system | user | assistant")
    content: str


class LLMRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[Message]
    temperature: float = 0.0
    max_tokens: int = 1024
    # When set, the provider should attempt to return a JSON object; providers
    # that cannot enforce this still return text that the caller parses/validates.
    json_schema: dict[str, Any] | None = None


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    model: str
    provider: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    raw: dict[str, Any] | None = None


class LLMProvider(abc.ABC):
    """A text-generation / structured-reasoning provider."""

    name: str = "base"

    @property
    @abc.abstractmethod
    def model(self) -> str: ...

    @property
    def sends_data_offhost(self) -> bool:
        """True if using this provider transmits evidence to an external service.

        Local and mock providers return False; hosted APIs return True. The
        privacy guard uses this to enforce ``private_mode``.
        """
        return True

    @abc.abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse: ...

    def complete(self, prompt: str, *, system: str | None = None, **kwargs: Any) -> str:
        """Convenience: single-prompt completion returning plain text."""
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        return self.generate(LLMRequest(messages=messages, **kwargs)).text


class EmbeddingProvider(abc.ABC):
    name: str = "base"

    @property
    @abc.abstractmethod
    def model(self) -> str: ...

    @property
    def dimensions(self) -> int:
        return 0

    @property
    def sends_data_offhost(self) -> bool:
        return True

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VisionObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.5


class VisionProvider(abc.ABC):
    name: str = "base"

    @property
    @abc.abstractmethod
    def model(self) -> str: ...

    @property
    def sends_data_offhost(self) -> bool:
        return True

    @abc.abstractmethod
    def describe_image(self, image: bytes, *, prompt: str | None = None) -> VisionObservation: ...


class TranscriptionProvider(abc.ABC):
    name: str = "base"

    @property
    @abc.abstractmethod
    def model(self) -> str: ...

    @property
    def sends_data_offhost(self) -> bool:
        return True

    @abc.abstractmethod
    def transcribe(self, audio: bytes, *, language: str | None = None) -> str: ...
