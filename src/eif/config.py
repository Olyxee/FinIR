"""Configuration for EIF.

Configuration can come from three layers, applied in increasing precedence:

1. Built-in defaults (this module).
2. A YAML/TOML config file (``eif.yaml`` / ``--config`` / ``EIF_CONFIG_FILE``).
3. Environment variables (prefix ``EIF_``, plus provider-native keys).

Everything has a sane default so that ``Config()`` alone yields a fully working,
fully local configuration (SQLite + deterministic mock provider).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .exceptions import ConfigurationError


class OrganizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = "demo-org"
    name: str | None = None
    currency: str = "ZAR"


class MaterialityConfig(BaseModel):
    """Thresholds above which an impact is considered material.

    An event is material if its primary impact's absolute expected value exceeds
    ``absolute``, OR exceeds ``relative_revenue * annual_revenue`` (cost metrics
    use ``relative_cost * annual_cost`` when those baselines are provided).
    """

    model_config = ConfigDict(extra="forbid")
    absolute: float = 500_000.0
    relative_revenue: float = 0.01
    relative_cost: float = 0.02
    annual_revenue: float | None = None
    annual_cost: float | None = None


class ModelRole(BaseModel):
    """Which provider/model backs a named role (reasoning, extraction, ...)."""

    model_config = ConfigDict(extra="forbid")
    provider: str = "mock"
    model: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reasoning: ModelRole = Field(default_factory=ModelRole)
    extraction: ModelRole = Field(default_factory=ModelRole)
    embeddings: ModelRole = Field(default_factory=ModelRole)
    vision: ModelRole = Field(default_factory=ModelRole)
    transcription: ModelRole = Field(default_factory=ModelRole)


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_file_bytes: int = 25 * 1024 * 1024
    redact_pii: bool = False
    allowed_mime_prefixes: list[str] = Field(
        default_factory=lambda: [
            "text/",
            "message/",
            "application/json",
            "application/pdf",
            "application/vnd",
        ]
    )


class StorageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database_url: str = "sqlite:///./eif.db"
    echo_sql: bool = False


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: str = "INFO"
    format: str = "json"  # json | text


class Config(BaseModel):
    """Top-level EIF configuration object."""

    model_config = ConfigDict(extra="forbid")

    organization: OrganizationConfig = Field(default_factory=OrganizationConfig)
    materiality: MaterialityConfig = Field(default_factory=MaterialityConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    private_mode: bool = False

    # ------------------------------------------------------------------ loaders
    @classmethod
    def load(cls, path: str | Path | None = None, *, apply_env: bool = True) -> Config:
        """Load config from an optional YAML/TOML file, then overlay env vars."""
        data: dict[str, Any] = {}
        file_path = _resolve_config_path(path)
        if file_path is not None:
            data = _read_config_file(file_path)
        cfg = cls.model_validate(data)
        if apply_env:
            cfg = cfg._apply_env(os.environ)
        return cfg

    def _apply_env(self, env: dict[str, str] | os._Environ[str]) -> Config:
        """Overlay recognized environment variables (highest precedence)."""
        cfg = self.model_copy(deep=True)

        if v := env.get("EIF_ORGANIZATION_ID"):
            cfg.organization.id = v
        if v := env.get("EIF_ORGANIZATION_CURRENCY"):
            cfg.organization.currency = v
        if v := env.get("EIF_DATABASE_URL"):
            cfg.storage.database_url = v
        if v := env.get("EIF_LOG_LEVEL"):
            cfg.logging.level = v
        if v := env.get("EIF_LOG_FORMAT"):
            cfg.logging.format = v
        if v := env.get("EIF_DEFAULT_LLM_PROVIDER"):
            cfg.models.reasoning.provider = v
            cfg.models.extraction.provider = v
        if v := env.get("EIF_MAX_FILE_BYTES"):
            cfg.security.max_file_bytes = int(v)
        if v := env.get("EIF_REDACT_PII"):
            cfg.security.redact_pii = _as_bool(v)
        if v := env.get("EIF_PRIVATE_MODE"):
            cfg.private_mode = _as_bool(v)
        return cfg

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_config_path(path: str | Path | None) -> Path | None:
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise ConfigurationError(f"Config file not found: {p}")
        return p
    env_path = os.environ.get("EIF_CONFIG_FILE")
    if env_path:
        p = Path(env_path)
        if not p.exists():
            raise ConfigurationError(f"EIF_CONFIG_FILE points to a missing file: {p}")
        return p
    for candidate in ("eif.yaml", "eif.yml"):
        p = Path(candidate)
        if p.exists():
            return p
    return None


def _read_config_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            loaded = yaml.safe_load(text) or {}
        elif suffix == ".toml":
            import tomllib

            loaded = tomllib.loads(text)
        else:
            raise ConfigurationError(f"Unsupported config format: {suffix}")
    except Exception as exc:
        raise ConfigurationError(f"Failed to parse config file {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Config file {path} must contain a mapping at the top level.")
    return loaded
