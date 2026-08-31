"""EIF exception hierarchy.

All exceptions raised deliberately by the framework derive from :class:`EIFError`
so that callers can catch the whole family with a single ``except``. Each carries
an optional machine-readable ``code`` used by the API layer to produce structured
error responses.
"""

from __future__ import annotations


class EIFError(Exception):
    """Base class for all framework errors."""

    code: str = "eif_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ConfigurationError(EIFError):
    """Invalid or missing configuration."""

    code = "configuration_error"


class ProviderError(EIFError):
    """A model provider failed or is not available/installed."""

    code = "provider_error"


class ProviderNotInstalledError(ProviderError):
    """An optional provider dependency is not installed."""

    code = "provider_not_installed"


class PrivacyViolationError(EIFError):
    """An operation would send data off-host while private mode is enabled."""

    code = "privacy_violation"


class ConnectorError(EIFError):
    """A connector failed to load or parse evidence."""

    code = "connector_error"


class UnsupportedModalityError(ConnectorError):
    """No connector/parser is registered for the requested modality/format."""

    code = "unsupported_modality"


class ValidationError(EIFError):
    """Domain-level validation failure (distinct from pydantic's ValidationError)."""

    code = "validation_error"


class StorageError(EIFError):
    """A persistence backend failed."""

    code = "storage_error"


class NotFoundError(EIFError):
    """A requested object does not exist."""

    code = "not_found"


class RegistryError(EIFError):
    """An ontology registry lookup or registration failed."""

    code = "registry_error"


class SecurityError(EIFError):
    """A security constraint (file size, MIME, path safety) was violated."""

    code = "security_error"
