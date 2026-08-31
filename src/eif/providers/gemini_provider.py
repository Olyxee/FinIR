"""Google Gemini LLM provider (optional dependency)."""

from __future__ import annotations

import os
from typing import Any

from ..exceptions import ProviderError, ProviderNotInstalledError
from .base import LLMProvider, LLMRequest, LLMResponse, TokenUsage


class GeminiLLMProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self, model: str = "gemini-1.5-flash", *, options: dict[str, Any] | None = None
    ) -> None:
        self._model = model
        self._options = options or {}

    @property
    def model(self) -> str:
        return self._model

    def _model_client(self) -> Any:
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ProviderNotInstalledError(
                "The 'google-generativeai' package is required for the Gemini provider. "
                "Install with: pip install 'economic-intelligence-framework[gemini]'"
            ) from exc
        api_key = self._options.get("api_key") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ProviderError("Gemini provider requires GEMINI_API_KEY.")
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(self._model)

    def generate(self, request: LLMRequest) -> LLMResponse:
        model = self._model_client()
        prompt = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in request.messages)
        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_tokens,
        }
        if request.json_schema is not None:
            generation_config["response_mime_type"] = "application/json"
        try:
            resp = model.generate_content(prompt, generation_config=generation_config)
        except Exception as exc:
            raise ProviderError(f"Gemini request failed: {exc}") from exc
        usage_meta = getattr(resp, "usage_metadata", None)
        usage = TokenUsage(
            prompt_tokens=getattr(usage_meta, "prompt_token_count", 0) or 0,
            completion_tokens=getattr(usage_meta, "candidates_token_count", 0) or 0,
            total_tokens=getattr(usage_meta, "total_token_count", 0) or 0,
        )
        return LLMResponse(
            text=getattr(resp, "text", "") or "",
            model=self._model,
            provider=self.name,
            usage=usage,
        )
