"""Entity resolution and event resolution.

These interfaces decide whether new information refers to something EIF already
knows about. They are pluggable — swap in embedding-based or ML resolvers — but
the shipped defaults are deterministic and inspectable.

* :class:`EntityResolver` collapses duplicate entities (``ABC Ltd`` == ``ABC``).
* :class:`EventResolver` decides whether a freshly generated event *candidate*
  reinforces, weakens, contradicts, resolves, or is distinct from existing events.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import timedelta

from ..domain import EconomicEntity, EconomicEvent
from ..domain.enums import Direction
from ..storage.base import EntityQuery, EventQuery, Repository

# Actions an event resolver can recommend for a candidate against an existing event.
ACTION_NEW = "new"
ACTION_REINFORCE = "reinforce"
ACTION_WEAKEN = "weaken"
ACTION_CONTRADICT = "contradict"
ACTION_RESOLVE = "resolve"


@dataclass
class EntityResolution:
    entity: EconomicEntity
    created: bool
    rationale: str


class EntityResolver(abc.ABC):
    @abc.abstractmethod
    def resolve(self, entity: EconomicEntity, repo: Repository) -> EntityResolution: ...


class DefaultEntityResolver(EntityResolver):
    """Deterministic resolver: exact dedup key, then name/alias overlap within type."""

    def resolve(self, entity: EconomicEntity, repo: Repository) -> EntityResolution:
        existing = repo.find_entity_by_key(entity.dedup_key())
        if existing is not None:
            merged = repo.upsert_entity(entity)  # merges aliases/attrs
            return EntityResolution(entity=merged, created=False, rationale="exact dedup key match")

        # Fuzzy: same type, shared name/alias token set.
        candidates = repo.list_entities(
            EntityQuery(
                entity_type=entity.entity_type, organization_id=entity.organization_id, limit=1000
            )
        ).items
        target_names = entity.all_names()
        for cand in candidates:
            if cand.all_names() & target_names:
                cand.aliases = sorted({*cand.aliases, *entity.aliases, entity.name} - {cand.name})
                repo.upsert_entity(cand)
                return EntityResolution(
                    entity=repo.get_entity(cand.id) or cand,
                    created=False,
                    rationale=f"name overlap with existing entity {cand.id}",
                )

        created = repo.upsert_entity(entity)
        return EntityResolution(
            entity=created, created=True, rationale="no match; created new entity"
        )


@dataclass
class EventMatch:
    """The resolver's recommendation for a candidate event."""

    action: str
    matched_event: EconomicEvent | None = None
    similarity: float = 0.0
    rationale: str = ""


class EventResolver(abc.ABC):
    @abc.abstractmethod
    def match(self, candidate: EconomicEvent, repo: Repository) -> EventMatch: ...


class DefaultEventResolver(EventResolver):
    """Deterministic event resolver.

    Matches a candidate to an existing *open* event of the same type that shares
    at least one entity and falls within ``window_days`` of effective/detected
    time. Direction/magnitude then decides reinforce vs weaken vs contradict.
    """

    def __init__(self, window_days: int = 120, min_entity_overlap: int = 1) -> None:
        self.window = timedelta(days=window_days)
        self.min_entity_overlap = min_entity_overlap

    def match(self, candidate: EconomicEvent, repo: Repository) -> EventMatch:
        existing = repo.list_events(
            EventQuery(
                organization_id=candidate.organization_id,
                event_type=candidate.event_type,
                limit=1000,
            )
        ).items
        cand_entities = set(candidate.entity_ids())
        best: EventMatch = EventMatch(action=ACTION_NEW, rationale="no comparable open event found")
        best_score = 0.0

        for ev in existing:
            if not ev.is_open():
                continue
            overlap = cand_entities & set(ev.entity_ids())
            if len(overlap) < self.min_entity_overlap:
                continue
            if not self._within_window(candidate, ev):
                continue
            score = len(overlap) / max(1, len(cand_entities | set(ev.entity_ids())))
            if score >= best_score:
                best_score = score
                best = EventMatch(
                    action=self._decide_action(candidate, ev),
                    matched_event=ev,
                    similarity=round(score, 3),
                    rationale=(
                        f"matched open {ev.event_type} {ev.id} on {len(overlap)} shared entit"
                        f"{'y' if len(overlap) == 1 else 'ies'}"
                    ),
                )
        return best

    def _within_window(self, candidate: EconomicEvent, existing: EconomicEvent) -> bool:
        a = candidate.effective_at or candidate.detected_at
        b = existing.effective_at or existing.detected_at
        return abs(a - b) <= self.window

    def _decide_action(self, candidate: EconomicEvent, existing: EconomicEvent) -> str:
        cand_dir = _primary_direction(candidate)
        exist_dir = _primary_direction(existing)
        if cand_dir == Direction.NEUTRAL or exist_dir == Direction.NEUTRAL:
            return ACTION_REINFORCE
        if cand_dir == exist_dir:
            return ACTION_REINFORCE
        if cand_dir != Direction.UNKNOWN and exist_dir != Direction.UNKNOWN:
            return ACTION_CONTRADICT
        return ACTION_REINFORCE


def _primary_direction(event: EconomicEvent) -> Direction:
    impact = event.primary_impact()
    if impact is not None:
        return Direction(impact.direction)
    return Direction.UNKNOWN
