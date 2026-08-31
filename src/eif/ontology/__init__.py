"""Extensible ontology registries for events, entities, and metrics.

These registries hold the framework's *open* vocabularies. Register your own
definitions at import time to extend EIF without forking it::

    from eif.ontology import EVENT_REGISTRY, EventTypeDefinition

    EVENT_REGISTRY.register(EventTypeDefinition(
        key="fx_exposure_change",
        label="FX Exposure Change",
        category="risk",
        default_metrics=["operating_income"],
    ))
"""

from __future__ import annotations

from .entities import ENTITY_REGISTRY, EntityTypeDefinition, is_known_entity_type
from .events import EVENT_REGISTRY, EventTypeDefinition, is_known_event_type
from .metrics import METRIC_REGISTRY, MetricDefinition
from .registry import Registry

__all__ = [
    "ENTITY_REGISTRY",
    "EVENT_REGISTRY",
    "METRIC_REGISTRY",
    "EntityTypeDefinition",
    "EventTypeDefinition",
    "MetricDefinition",
    "Registry",
    "is_known_entity_type",
    "is_known_event_type",
]
