"""Repository interface for persisting the EIF domain and event graph.

A single :class:`Repository` abstraction covers every core object plus the graph
edges and realized outcomes. This keeps the surface small and lets the event
graph, pipeline, API, and CLI all program against one interface. Concrete
backends:

* :class:`~eif.storage.memory.MemoryRepository` — in-memory, zero-dependency.
* :class:`~eif.storage.sql.repository.SqlRepository` — SQLAlchemy (SQLite/Postgres).

The interface is deliberately storage-agnostic so a future Neo4j / graph-DB
adapter can implement it without changing callers.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generic, TypeVar

from ..domain import (
    EconomicEntity,
    EconomicEvent,
    EconomicImpact,
    EventRelationship,
    Evidence,
    Observation,
    RealizedOutcome,
)

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """A page of results plus enough metadata for cursor-free pagination."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


@dataclass
class EventQuery:
    """Filter/paging options for listing events."""

    organization_id: str | None = None
    event_type: str | None = None
    status: str | None = None
    materiality: str | None = None
    entity_id: str | None = None
    detected_after: datetime | None = None
    detected_before: datetime | None = None
    limit: int = 50
    offset: int = 0
    order_desc: bool = True


@dataclass
class EntityQuery:
    organization_id: str | None = None
    entity_type: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass
class RepositoryStats:
    evidence: int = 0
    observations: int = 0
    entities: int = 0
    events: int = 0
    relationships: int = 0
    outcomes: int = 0
    extra: dict[str, int] = field(default_factory=dict)


class Repository(abc.ABC):
    """Abstract persistence + graph store for all EIF objects."""

    # -- lifecycle -----------------------------------------------------------
    def init_schema(self) -> None:  # pragma: no cover - default no-op
        """Create underlying schema if needed. No-op for in-memory backends."""

    def close(self) -> None:  # pragma: no cover - default no-op
        """Release resources."""

    # -- evidence ------------------------------------------------------------
    @abc.abstractmethod
    def add_evidence(self, evidence: Evidence) -> Evidence: ...

    @abc.abstractmethod
    def get_evidence(self, evidence_id: str) -> Evidence | None: ...

    @abc.abstractmethod
    def list_evidence(self, *, limit: int = 50, offset: int = 0) -> Page[Evidence]: ...

    # -- observations --------------------------------------------------------
    @abc.abstractmethod
    def add_observation(self, observation: Observation) -> Observation: ...

    @abc.abstractmethod
    def get_observation(self, observation_id: str) -> Observation | None: ...

    @abc.abstractmethod
    def list_observations(self, *, limit: int = 50, offset: int = 0) -> Page[Observation]: ...

    # -- entities ------------------------------------------------------------
    @abc.abstractmethod
    def upsert_entity(self, entity: EconomicEntity) -> EconomicEntity:
        """Insert the entity, or return the existing one sharing its dedup key."""

    @abc.abstractmethod
    def get_entity(self, entity_id: str) -> EconomicEntity | None: ...

    @abc.abstractmethod
    def find_entity_by_key(self, dedup_key: str) -> EconomicEntity | None: ...

    @abc.abstractmethod
    def list_entities(self, query: EntityQuery | None = None) -> Page[EconomicEntity]: ...

    # -- events --------------------------------------------------------------
    @abc.abstractmethod
    def add_event(self, event: EconomicEvent) -> EconomicEvent: ...

    @abc.abstractmethod
    def update_event(self, event: EconomicEvent) -> EconomicEvent: ...

    @abc.abstractmethod
    def get_event(self, event_id: str) -> EconomicEvent | None: ...

    @abc.abstractmethod
    def list_events(self, query: EventQuery | None = None) -> Page[EconomicEvent]: ...

    # -- relationships -------------------------------------------------------
    @abc.abstractmethod
    def add_relationship(self, relationship: EventRelationship) -> EventRelationship: ...

    @abc.abstractmethod
    def list_relationships(self, *, event_id: str | None = None) -> list[EventRelationship]: ...

    # -- outcomes ------------------------------------------------------------
    @abc.abstractmethod
    def add_outcome(self, outcome: RealizedOutcome) -> RealizedOutcome: ...

    @abc.abstractmethod
    def get_outcome_for_event(self, event_id: str) -> RealizedOutcome | None: ...

    @abc.abstractmethod
    def list_outcomes(self, *, limit: int = 50, offset: int = 0) -> Page[RealizedOutcome]: ...

    # -- derived / convenience ----------------------------------------------
    def list_impacts(self, *, limit: int = 50, offset: int = 0) -> Page[EconomicImpact]:
        """Flatten impacts across events (default implementation)."""
        events = self.list_events(EventQuery(limit=10_000, offset=0)).items
        impacts = [i for e in events for i in e.impacts]
        total = len(impacts)
        return Page(items=impacts[offset : offset + limit], total=total, limit=limit, offset=offset)

    @abc.abstractmethod
    def stats(self) -> RepositoryStats: ...
