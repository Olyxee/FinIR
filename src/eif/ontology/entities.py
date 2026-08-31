"""The entity-type ontology."""

from __future__ import annotations

from ..domain.base import EIFModel
from .registry import Registry


class EntityTypeDefinition(EIFModel):
    """Definition of an economic entity type."""

    key: str
    label: str
    description: str = ""


ENTITY_REGISTRY: Registry[EntityTypeDefinition] = Registry("entity_types")

_DEFAULT_ENTITY_TYPES: tuple[tuple[str, str], ...] = (
    ("organization", "Organization"),
    ("business_unit", "Business Unit"),
    ("customer", "Customer"),
    ("supplier", "Supplier"),
    ("employee", "Employee"),
    ("asset", "Asset"),
    ("product", "Product"),
    ("service", "Service"),
    ("project", "Project"),
    ("contract", "Contract"),
    ("invoice", "Invoice"),
    ("order", "Order"),
    ("account", "Account"),
    ("location", "Location"),
    ("resource", "Resource"),
)


def _seed() -> None:
    for key, label in _DEFAULT_ENTITY_TYPES:
        if not ENTITY_REGISTRY.has(key):
            ENTITY_REGISTRY.register(EntityTypeDefinition(key=key, label=label))


_seed()


def is_known_entity_type(key: str) -> bool:
    return ENTITY_REGISTRY.has(key)
