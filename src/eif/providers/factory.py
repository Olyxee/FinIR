"""Provider factory and privacy guard.

Turns a :class:`~eif.config.ModelRole` (``provider`` + ``model`` + ``options``)
into a concrete provider instance, lazily importing optional backends only when
requested. Also enforces ``private_mode``: any attempt to construct a provider
that would transmit evidence off-host raises :class:`PrivacyViolationError`.
"""

from __future__ import annotations

from typing import Any

from ..config import ModelRole
from ..exceptions import PrivacyViolationError, ProviderError
from .base import EmbeddingProvider, LLMProvider, TranscriptionProvider, VisionProvider
from .mock import (
    MockEmbeddingProvider,
    MockLLMProvider,
    MockTranscriptionProvider,
    MockVisionProvider,
)


def build_llm_provider(role: ModelRole, *, private_mode: bool = False) -> LLMProvider:
    provider = role.provider.lower()
    if provider in ("mock", "deterministic", "none"):
        return MockLLMProvider(model=role.model or "mock-llm-v1")

    instance: LLMProvider
    if provider in ("openai", "local", "openai-compatible"):
        from .openai_provider import OpenAILLMProvider

        instance = OpenAILLMProvider(
            model=role.model or "gpt-4o-mini", options=_with_local_flag(role, provider)
        )
    elif provider == "anthropic":
        from .anthropic_provider import AnthropicLLMProvider

        instance = AnthropicLLMProvider(
            model=role.model or "claude-3-5-sonnet-latest", options=role.options
        )
    elif provider == "gemini":
        from .gemini_provider import GeminiLLMProvider

        instance = GeminiLLMProvider(model=role.model or "gemini-1.5-flash", options=role.options)
    else:
        raise ProviderError(f"Unknown LLM provider: {role.provider!r}")

    _guard_privacy(instance, private_mode)
    return instance


def build_embedding_provider(role: ModelRole, *, private_mode: bool = False) -> EmbeddingProvider:
    provider = role.provider.lower()
    if provider in ("mock", "deterministic", "local", "none"):
        return MockEmbeddingProvider(model=role.model or "mock-embed-v1")
    if provider in ("openai", "openai-compatible"):
        from .openai_provider import OpenAIEmbeddingProvider

        instance = OpenAIEmbeddingProvider(
            model=role.model or "text-embedding-3-small",
            options=_with_local_flag(role, provider),
        )
        _guard_privacy(instance, private_mode)
        return instance
    raise ProviderError(f"Unknown embedding provider: {role.provider!r}")


def build_vision_provider(role: ModelRole, *, private_mode: bool = False) -> VisionProvider:
    provider = role.provider.lower()
    if provider in ("mock", "deterministic", "none"):
        return MockVisionProvider(model=role.model or "mock-vision-v1")
    # Real vision adapters are pluggable; ship a clean interface + mock default.
    raise ProviderError(
        f"No built-in vision provider for {role.provider!r}; register a custom VisionProvider."
    )


def build_transcription_provider(
    role: ModelRole, *, private_mode: bool = False
) -> TranscriptionProvider:
    provider = role.provider.lower()
    if provider in ("mock", "deterministic", "none"):
        return MockTranscriptionProvider(model=role.model or "mock-transcribe-v1")
    raise ProviderError(
        f"No built-in transcription provider for {role.provider!r}; "
        "register a custom TranscriptionProvider."
    )


def _with_local_flag(role: ModelRole, provider: str) -> dict[str, Any]:
    options = dict(role.options)
    if provider == "local" and "base_url" not in options:
        # 'local' means an OpenAI-compatible endpoint; require an explicit base_url
        # but default to the common localhost port if unset.
        options.setdefault("base_url", "http://localhost:11434/v1")
    return options


def _guard_privacy(provider: object, private_mode: bool) -> None:
    if private_mode and getattr(provider, "sends_data_offhost", True):
        raise PrivacyViolationError(
            f"Provider '{getattr(provider, 'name', '?')}' would transmit evidence off-host, "
            "but private_mode is enabled. Use a local or mock provider."
        )
