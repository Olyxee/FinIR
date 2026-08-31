"""Provider tests, including the privacy guard."""

from __future__ import annotations

import pytest

from eif.config import ModelRole
from eif.exceptions import PrivacyViolationError, ProviderError
from eif.providers import (
    MockEmbeddingProvider,
    MockLLMProvider,
    build_embedding_provider,
    build_llm_provider,
)
from eif.providers.base import LLMRequest, Message


def test_mock_llm_deterministic():
    p = MockLLMProvider()
    a = p.complete("hello")
    b = p.complete("hello")
    assert a == b
    assert p.sends_data_offhost is False


def test_mock_llm_json_schema():
    p = MockLLMProvider()
    resp = p.generate(
        LLMRequest(
            messages=[Message(role="user", content="x")],
            json_schema={"properties": {"n": {"type": "number"}, "s": {"type": "string"}}},
        )
    )
    import json

    obj = json.loads(resp.text)
    assert "n" in obj and "s" in obj


def test_mock_embeddings_unit_norm():
    p = MockEmbeddingProvider(dim=32)
    v = p.embed(["a", "b"])
    assert len(v) == 2 and len(v[0]) == 32
    norm = sum(x * x for x in v[0]) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_build_mock_provider():
    p = build_llm_provider(ModelRole(provider="mock"))
    assert p.name == "mock"


def test_privacy_guard_blocks_offhost():
    role = ModelRole(provider="openai", model="gpt-4o-mini", options={"api_key": "x"})
    with pytest.raises(PrivacyViolationError):
        build_llm_provider(role, private_mode=True)


def test_unknown_provider_raises():
    with pytest.raises(ProviderError):
        build_llm_provider(ModelRole(provider="does-not-exist"))


def test_local_embeddings_allowed_in_private_mode():
    # local/mock embeddings must be permitted even in private mode
    p = build_embedding_provider(ModelRole(provider="local"), private_mode=True)
    assert p.sends_data_offhost is False
