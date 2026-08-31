# Model Providers

EIF is model-agnostic. It talks to four kinds of providers through narrow
interfaces, so any backend can be swapped in without touching the pipeline.

## Capability interfaces

| Interface | Method | Used for |
|-----------|--------|----------|
| `LLMProvider` | `generate` / `complete` | interpretation, classification, assumptions |
| `EmbeddingProvider` | `embed` | similarity, future entity resolution |
| `VisionProvider` | `describe_image` | image evidence |
| `TranscriptionProvider` | `transcribe` | audio evidence |

Each exposes `sends_data_offhost`, which the privacy guard uses.

## Default: deterministic mock

The default provider is a fully-local, deterministic mock (no network, no keys).
It makes the entire framework — pipeline, CLI, API, benchmark — run and be tested
offline. It is reproducible, not accurate; use a real provider for production
interpretation.

## Optional adapters

| Provider | Extra | Notes |
|----------|-------|-------|
| OpenAI / OpenAI-compatible | `[openai]` | Honors `OPENAI_BASE_URL` for Azure/vLLM/Ollama/LM Studio; a base URL is treated as local. |
| Anthropic | `[anthropic]` | `ANTHROPIC_API_KEY`. |
| Gemini | `[gemini]` | `GEMINI_API_KEY`. |

Missing an optional dependency raises a clear `ProviderNotInstalledError`.

## Configuration

Roles map to providers/models in config (env or YAML):

```yaml
models:
  reasoning:
    provider: openai
    model: gpt-4o-mini
  extraction:
    provider: anthropic
    model: claude-3-5-sonnet-latest
  embeddings:
    provider: local
```

Build one directly:

```python
from eif.providers import build_llm_provider
from eif.config import ModelRole

llm = build_llm_provider(ModelRole(provider="mock"))
print(llm.complete("hello"))
```

## Privacy guard

With `private_mode: true`, constructing any provider that would transmit evidence
off-host raises `PrivacyViolationError`. Local and mock providers are always
allowed. See [privacy.md](privacy.md).

## Writing a provider

Implement the relevant interface (e.g. `LLMProvider.generate` returning an
`LLMResponse`) and set `sends_data_offhost` appropriately. That's the whole
contract.
