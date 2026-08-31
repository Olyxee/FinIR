"""The persistent Economic Event Graph.

Events live in the graph across many analysis runs. New evidence integrates into
existing events rather than spawning disconnected duplicates:

    reinforce  -> raise confidence, attach evidence, confirm
    contradict -> lower confidence, record contradicting evidence, weaken
    resolve    -> close the event with its realized outcome

The graph is a thin, well-tested layer over a :class:`Repository` and the
pluggable resolvers, so it works identically over the in-memory and SQL backends
and could be re-implemented over a native graph DB behind the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import (
    Confidence,
    EconomicEvent,
    EventRelationship,
    RealizedOutcome,
)
from ..domain.enums import EventStatus, EvidenceStance, RelationshipType
from ..domain.provenance import Citation
from ..storage.base import Repository
from .resolution import (
    ACTION_CONTRADICT,
    ACTION_NEW,
    ACTION_REINFORCE,
    ACTION_RESOLVE,
    ACTION_WEAKEN,
    DefaultEntityResolver,
    DefaultEventResolver,
    EntityResolver,
    EventResolver,
)


@dataclass
class IntegrationResult:
    """Outcome of integrating one candidate event into the graph."""

    event: EconomicEvent
    action: str
    created: bool
    rationale: str


def _noisy_or(a: float, b: float) -> float:
    """Combine two independent confidences (bounded, monotonic)."""
    return 1.0 - (1.0 - a) * (1.0 - b)


class EventGraph:
    """High-level API over the event graph."""

    def __init__(
        self,
        repo: Repository,
        *,
        entity_resolver: EntityResolver | None = None,
        event_resolver: EventResolver | None = None,
    ) -> None:
        self.repo = repo
        self.entity_resolver = entity_resolver or DefaultEntityResolver()
        self.event_resolver = event_resolver or DefaultEventResolver()

    # ------------------------------------------------------------------ integrate
    def integrate(self, candidate: EconomicEvent) -> IntegrationResult:
        """Integrate a candidate event, updating the graph in place as needed."""
        match = self.event_resolver.match(candidate, self.repo)

        if match.action == ACTION_NEW or match.matched_event is None:
            saved = self.repo.add_event(candidate)
            return IntegrationResult(
                event=saved, action=ACTION_NEW, created=True, rationale=match.rationale
            )

        existing = match.matched_event
        if match.action == ACTION_REINFORCE:
            updated = self._reinforce(existing, candidate, match.rationale)
        elif match.action in (ACTION_CONTRADICT, ACTION_WEAKEN):
            updated = self._contradict(existing, candidate, match.rationale)
        elif match.action == ACTION_RESOLVE:
            updated = self._mark_resolved(existing, candidate)
        else:  # pragma: no cover - defensive
            updated = self._reinforce(existing, candidate, match.rationale)

        saved = self.repo.update_event(updated)
        return IntegrationResult(
            event=saved, action=match.action, created=False, rationale=match.rationale
        )

    def _reinforce(
        self, existing: EconomicEvent, candidate: EconomicEvent, rationale: str
    ) -> EconomicEvent:
        existing.add_evidence(candidate.evidence_ids, candidate.observation_ids)
        existing.entities = _merge_entities(existing, candidate)
        existing.confidence = Confidence(
            score=_noisy_or(existing.confidence.score, candidate.confidence.score),
            rationale=f"reinforced: {rationale}",
        )
        # Adopt candidate impacts if it carries a higher-confidence estimate.
        if candidate.impacts and (
            not existing.impacts or _max_impact_conf(candidate) > _max_impact_conf(existing)
        ):
            existing.impacts = candidate.impacts
            existing.affected_metrics = sorted(
                {*existing.affected_metrics, *candidate.affected_metrics}
            )
        existing.effective_at = existing.effective_at or candidate.effective_at
        existing.status = EventStatus.CONFIRMED
        existing.merge_provenance(candidate.provenance)
        existing.touch()
        return existing

    def _contradict(
        self, existing: EconomicEvent, candidate: EconomicEvent, rationale: str
    ) -> EconomicEvent:
        penalty = 0.5 * candidate.confidence.score
        new_score = max(0.0, existing.confidence.score * (1.0 - penalty))
        existing.confidence = Confidence(
            score=new_score,
            conflict_penalty=penalty,
            rationale=f"contradicted: {rationale}",
        )
        for ev_id in candidate.evidence_ids:
            existing.provenance.citations.append(
                Citation(evidence_id=ev_id, stance=EvidenceStance.CONTRADICTS)
            )
        existing.add_evidence([], candidate.observation_ids)
        existing.status = EventStatus.WEAKENED
        existing.touch()
        return existing

    def _mark_resolved(self, existing: EconomicEvent, candidate: EconomicEvent) -> EconomicEvent:
        existing.status = EventStatus.RESOLVED
        existing.resolved_at = candidate.detected_at
        existing.touch()
        return existing

    # ------------------------------------------------------------------ relationships
    def relate(
        self,
        source_event_id: str,
        target_event_id: str,
        rel_type: RelationshipType,
        *,
        confidence: float = 0.7,
        note: str | None = None,
    ) -> EventRelationship:
        rel = EventRelationship(
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            type=rel_type,
            confidence=Confidence(score=confidence),
            note=note,
        )
        return self.repo.add_relationship(rel)

    def neighbors(self, event_id: str) -> list[EconomicEvent]:
        """Return events directly connected to ``event_id`` by any relationship."""
        rels = self.repo.list_relationships(event_id=event_id)
        neighbor_ids = {
            (r.target_event_id if r.source_event_id == event_id else r.source_event_id)
            for r in rels
        }
        out = [self.repo.get_event(i) for i in neighbor_ids]
        return [e for e in out if e is not None]

    # ------------------------------------------------------------------ outcomes
    def record_outcome(self, outcome: RealizedOutcome) -> EconomicEvent | None:
        """Attach a realized outcome and reconcile the event's impacts/status."""
        self.repo.add_outcome(outcome)
        event = self.repo.get_event(outcome.event_id)
        if event is None:
            return None
        for impact in event.impacts:
            if impact.metric in outcome.realized_metrics:
                impact.actual_value = outcome.realized_metrics[impact.metric]
                impact.actual_recorded_at = outcome.recorded_at
        if outcome.occurred:
            event.status = EventStatus.RESOLVED
            event.resolved_at = outcome.realized_at or outcome.recorded_at
        else:
            event.status = EventStatus.DISMISSED
        event.touch()
        return self.repo.update_event(event)


def _merge_entities(existing: EconomicEvent, candidate: EconomicEvent):
    seen = {e.entity_id for e in existing.entities}
    merged = list(existing.entities)
    for ref in candidate.entities:
        if ref.entity_id not in seen:
            merged.append(ref)
            seen.add(ref.entity_id)
    return merged


def _max_impact_conf(event: EconomicEvent) -> float:
    return max((i.estimate.confidence for i in event.impacts), default=0.0)
