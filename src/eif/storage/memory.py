"""In-memory repository.

Zero-dependency implementation used for tests, the deterministic default, and
quick experiments. Objects are stored as deep copies so callers cannot mutate
persisted state by holding a reference — matching the semantics of a real DB.
"""

from __future__ import annotations

from ..domain import (
    EconomicEntity,
    EconomicEvent,
    EventRelationship,
    Evidence,
    Observation,
    RealizedOutcome,
)
from .base import (
    EntityQuery,
    EventQuery,
    Page,
    Repository,
    RepositoryStats,
)


class MemoryRepository(Repository):
    def __init__(self) -> None:
        self._evidence: dict[str, Evidence] = {}
        self._observations: dict[str, Observation] = {}
        self._entities: dict[str, EconomicEntity] = {}
        self._entity_keys: dict[str, str] = {}  # dedup_key -> entity_id
        self._events: dict[str, EconomicEvent] = {}
        self._relationships: dict[str, EventRelationship] = {}
        self._outcomes: dict[str, RealizedOutcome] = {}

    # -- evidence ------------------------------------------------------------
    def add_evidence(self, evidence: Evidence) -> Evidence:
        self._evidence[evidence.id] = evidence.model_copy(deep=True)
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        found = self._evidence.get(evidence_id)
        return found.model_copy(deep=True) if found else None

    def list_evidence(self, *, limit: int = 50, offset: int = 0) -> Page[Evidence]:
        items = sorted(self._evidence.values(), key=lambda e: e.ingested_at, reverse=True)
        return _page([e.model_copy(deep=True) for e in items], limit, offset)

    # -- observations --------------------------------------------------------
    def add_observation(self, observation: Observation) -> Observation:
        self._observations[observation.id] = observation.model_copy(deep=True)
        return observation

    def get_observation(self, observation_id: str) -> Observation | None:
        found = self._observations.get(observation_id)
        return found.model_copy(deep=True) if found else None

    def list_observations(self, *, limit: int = 50, offset: int = 0) -> Page[Observation]:
        items = list(self._observations.values())
        return _page([o.model_copy(deep=True) for o in items], limit, offset)

    # -- entities ------------------------------------------------------------
    def upsert_entity(self, entity: EconomicEntity) -> EconomicEntity:
        key = entity.dedup_key()
        existing_id = self._entity_keys.get(key)
        if existing_id is not None:
            existing = self._entities[existing_id]
            # Merge aliases / external ids into the canonical record.
            merged_aliases = sorted(
                {*existing.aliases, *entity.aliases, entity.name} - {existing.name}
            )
            existing.aliases = merged_aliases
            existing.external_ids = {**existing.external_ids, **entity.external_ids}
            existing.attributes = {**existing.attributes, **entity.attributes}
            return existing.model_copy(deep=True)
        self._entities[entity.id] = entity.model_copy(deep=True)
        self._entity_keys[key] = entity.id
        return entity

    def get_entity(self, entity_id: str) -> EconomicEntity | None:
        found = self._entities.get(entity_id)
        return found.model_copy(deep=True) if found else None

    def find_entity_by_key(self, dedup_key: str) -> EconomicEntity | None:
        entity_id = self._entity_keys.get(dedup_key)
        return self.get_entity(entity_id) if entity_id else None

    def list_entities(self, query: EntityQuery | None = None) -> Page[EconomicEntity]:
        q = query or EntityQuery()
        items = list(self._entities.values())
        if q.organization_id is not None:
            items = [e for e in items if e.organization_id == q.organization_id]
        if q.entity_type is not None:
            items = [e for e in items if e.entity_type == q.entity_type]
        return _page([e.model_copy(deep=True) for e in items], q.limit, q.offset)

    # -- events --------------------------------------------------------------
    def add_event(self, event: EconomicEvent) -> EconomicEvent:
        self._events[event.id] = event.model_copy(deep=True)
        return event

    def update_event(self, event: EconomicEvent) -> EconomicEvent:
        self._events[event.id] = event.model_copy(deep=True)
        return event

    def get_event(self, event_id: str) -> EconomicEvent | None:
        found = self._events.get(event_id)
        return found.model_copy(deep=True) if found else None

    def list_events(self, query: EventQuery | None = None) -> Page[EconomicEvent]:
        q = query or EventQuery()
        items = list(self._events.values())
        if q.organization_id is not None:
            items = [e for e in items if e.organization_id == q.organization_id]
        if q.event_type is not None:
            items = [e for e in items if e.event_type == q.event_type]
        if q.status is not None:
            items = [e for e in items if str(e.status) == q.status]
        if q.materiality is not None:
            items = [e for e in items if str(e.materiality) == q.materiality]
        if q.entity_id is not None:
            items = [e for e in items if q.entity_id in e.entity_ids()]
        if q.detected_after is not None:
            items = [e for e in items if e.detected_at >= q.detected_after]
        if q.detected_before is not None:
            items = [e for e in items if e.detected_at <= q.detected_before]
        items.sort(key=lambda e: e.detected_at, reverse=q.order_desc)
        return _page([e.model_copy(deep=True) for e in items], q.limit, q.offset)

    # -- relationships -------------------------------------------------------
    def add_relationship(self, relationship: EventRelationship) -> EventRelationship:
        self._relationships[relationship.id] = relationship.model_copy(deep=True)
        return relationship

    def list_relationships(self, *, event_id: str | None = None) -> list[EventRelationship]:
        rels = list(self._relationships.values())
        if event_id is not None:
            rels = [
                r for r in rels if r.source_event_id == event_id or r.target_event_id == event_id
            ]
        return [r.model_copy(deep=True) for r in rels]

    # -- outcomes ------------------------------------------------------------
    def add_outcome(self, outcome: RealizedOutcome) -> RealizedOutcome:
        self._outcomes[outcome.id] = outcome.model_copy(deep=True)
        return outcome

    def get_outcome_for_event(self, event_id: str) -> RealizedOutcome | None:
        for outcome in self._outcomes.values():
            if outcome.event_id == event_id:
                return outcome.model_copy(deep=True)
        return None

    def list_outcomes(self, *, limit: int = 50, offset: int = 0) -> Page[RealizedOutcome]:
        items = list(self._outcomes.values())
        return _page([o.model_copy(deep=True) for o in items], limit, offset)

    # -- stats ---------------------------------------------------------------
    def stats(self) -> RepositoryStats:
        return RepositoryStats(
            evidence=len(self._evidence),
            observations=len(self._observations),
            entities=len(self._entities),
            events=len(self._events),
            relationships=len(self._relationships),
            outcomes=len(self._outcomes),
        )


def _page(items: list, limit: int, offset: int) -> Page:
    total = len(items)
    return Page(items=items[offset : offset + limit], total=total, limit=limit, offset=offset)
