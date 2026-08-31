"""OpenAI-compatible LLM and embedding providers.

Works with the OpenAI API and any OpenAI-compatible endpoint (Azure OpenAI,
vLLM, Ollama's OpenAI shim, LM Studio, ...) by honoring ``base_url``. The
``openai`` package is an optional dependency; importing/using this provider
without it raises a clear :class:`ProviderNotInstalledError`.
"""

from __future__ import annotations

import os
from typing import Any

from ..exceptions import ProviderError, ProviderNotInstalledError
from .base import (
    EmbeddingProvider,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    TokenUsage,
)


def _client(options: dict[str, Any]) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on optional dep
        raise ProviderNotInstalledError(
            "The 'openai' package is required for the OpenAI provider. "
            "Install with: pip install 'economic-intelligence-framework[openai]'"
        ) from exc
    api_key = options.get("api_key") or os.environ.get("OPENAI_API_KEY")
    base_url = options.get("base_url") or os.environ.get("OPENAI_BASE_URL")
    if not api_key and not base_url:
        raise ProviderError("OpenAI provider requires OPENAI_API_KEY or a base_url.")
    return OpenAI(api_key=api_key or "not-needed", base_url=base_url)


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(
        self, model: str = "gpt-4o-mini", *, options: dict[str, Any] | None = None
    ) -> None:
        self._model = model
        self._options = options or {}
        self._is_local = bool(self._options.get("base_url") or os.environ.get("OPENAI_BASE_URL"))

    @property
    def model(self) -> str:
        return self._model

    @property
    def sends_data_offhost(self) -> bool:
        # A configured base_url is treated as local/self-hosted.
        return not self._is_local

    def generate(self, request: LLMRequest) -> LLMResponse:
        client = _client(self._options)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        choice = resp.choices[0]
        usage = TokenUsage(
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
        )
        return LLMResponse(
            text=choice.message.content or "",
            model=self._model,
            provider=self.name,
            usage=usage,
        )


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(
        self, model: str = "text-embedding-3-small", *, options: dict[str, Any] | None = None
    ) -> None:
        self._model = model
        self._options = options or {}

    @property
    def model(self) -> str:
        return self._model

    @property
    def sends_data_offhost(self) -> bool:
        return not (self._options.get("base_url") or os.environ.get("OPENAI_BASE_URL"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        client = _client(self._options)
        try:
            resp = client.embeddings.create(model=self._model, input=texts)
        except Exception as exc:
            raise ProviderError(f"OpenAI embedding request failed: {exc}") from exc
        return [d.embedding for d in resp.data]
