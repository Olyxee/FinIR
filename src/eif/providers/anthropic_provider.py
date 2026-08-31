"""Anthropic (Claude) LLM provider (optional dependency)."""

from __future__ import annotations

import os
from typing import Any

from ..exceptions import ProviderError, ProviderNotInstalledError
from .base import LLMProvider, LLMRequest, LLMResponse, Message, TokenUsage


class AnthropicLLMProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-latest",
        *,
        options: dict[str, Any] | None = None,
    ) -> None:
        self._model = model
        self._options = options or {}

    @property
    def model(self) -> str:
        return self._model

    def _client(self) -> Any:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderNotInstalledError(
                "The 'anthropic' package is required for the Anthropic provider. "
                "Install with: pip install 'economic-intelligence-framework[anthropic]'"
            ) from exc
        api_key = self._options.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("Anthropic provider requires ANTHROPIC_API_KEY.")
        return anthropic.Anthropic(api_key=api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._client()
        system_parts = [m.content for m in request.messages if m.role == "system"]
        turns = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        if request.json_schema is not None:
            turns.append(
                Message(
                    role="assistant",
                    content="Here is the JSON object:",
                ).model_dump()
            )
        try:
            resp = client.messages.create(
                model=self._model,
                system="\n".join(system_parts) or None,
                messages=turns,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = TokenUsage(
            prompt_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
            total_tokens=(getattr(resp.usage, "input_tokens", 0) or 0)
            + (getattr(resp.usage, "output_tokens", 0) or 0),
        )
        return LLMResponse(text=text, model=self._model, provider=self.name, usage=usage)
