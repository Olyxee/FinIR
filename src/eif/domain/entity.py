"""Economic entities.

``entity_type`` is a free string validated against the extensible entity registry
(see :mod:`eif.ontology.entities`) rather than an enum, so downstream users can
register new entity types without patching the framework.
"""

from __future__ import annotations

from pydantic import Field

from ..utils.ids import entity_key, new_id
from .base import EIFModel


class EconomicEntity(EIFModel):
    """A named participant in economic activity (supplier, customer, product...)."""

    id: str = Field(default_factory=lambda: new_id("entity"))
    entity_type: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    # External identifiers keyed by system, e.g. {"erp": "SUP-123", "duns": "..."}.
    external_ids: dict[str, str] = Field(default_factory=dict)
    organization_id: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)

    def dedup_key(self) -> str:
        """Stable key used by entity resolution to detect duplicates."""
        return entity_key(self.entity_type, self.name)

    def all_names(self) -> set[str]:
        """Lower-cased set of name + aliases for matching."""
        return {self.name.lower(), *(a.lower() for a in self.aliases)}


class EntityRef(EIFModel):
    """A lightweight reference to an entity, with the role it plays in context."""

    entity_id: str
    entity_type: str
    name: str
    role: str | None = Field(
        default=None, description="Role in the event, e.g. 'supplier', 'affected_product'."
    )
