"""Ontology registry and configuration tests."""

from __future__ import annotations

import pytest

from eif.config import Config
from eif.exceptions import ConfigurationError, RegistryError
from eif.ontology import EVENT_REGISTRY, EventTypeDefinition
from eif.ontology.registry import Registry


def test_default_event_types_present():
    assert EVENT_REGISTRY.has("supplier_price_change")
    assert EVENT_REGISTRY.has("customer_contraction")
    assert len(EVENT_REGISTRY) >= 20


def test_registry_extensible():
    reg: Registry[EventTypeDefinition] = Registry("test")
    reg.register(EventTypeDefinition(key="fx_exposure", label="FX", category="risk"))
    assert reg.has("fx_exposure")
    with pytest.raises(RegistryError):
        reg.register(EventTypeDefinition(key="fx_exposure", label="dup", category="risk"))
    with pytest.raises(RegistryError):
        reg.get("nope")


def test_config_defaults():
    cfg = Config()
    assert cfg.organization.currency == "ZAR"
    assert cfg.storage.database_url.startswith("sqlite")
    assert cfg.models.reasoning.provider == "mock"


def test_config_from_yaml(tmp_path):
    p = tmp_path / "eif.yaml"
    p.write_text(
        "organization:\n  id: acme\n  currency: USD\nmateriality:\n  absolute: 1000000\n",
        encoding="utf-8",
    )
    cfg = Config.load(p, apply_env=False)
    assert cfg.organization.id == "acme"
    assert cfg.organization.currency == "USD"
    assert cfg.materiality.absolute == 1_000_000


def test_config_env_overlay(monkeypatch):
    monkeypatch.setenv("EIF_ORGANIZATION_ID", "envorg")
    monkeypatch.setenv("EIF_PRIVATE_MODE", "true")
    cfg = Config.load(apply_env=True)
    assert cfg.organization.id == "envorg"
    assert cfg.private_mode is True


def test_config_missing_file_raises():
    with pytest.raises(ConfigurationError):
        Config.load("/nonexistent/eif.yaml")
