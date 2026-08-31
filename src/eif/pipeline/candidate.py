"""Event candidate generation.

Turns observations into candidate economic events using a transparent, ordered
rule set. Candidates are grouped by ``(event_type, direction, primary entities)``
so that genuinely conflicting signals produce *separate* candidates — which the
event graph then reconciles as reinforcement or contradiction rather than
silently averaging them away.

Measurements from entity-less "context" observations (e.g. a spend table) are
made available to every candidate, while entity-bearing measurements only reach
candidates that share that entity. This keeps a supplier's percentage from
leaking onto an unrelated customer event in the same batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain import (
    Confidence,
    EconomicEvent,
    EntityRef,
    Measurement,
    Observation,
)
from ..domain.enums import Direction, EventStatus
from ..domain.provenance import Provenance
from ..ontology.events import EVENT_REGISTRY
from .stages import EventCandidateGenerator

_PRIMARY_ENTITY_TYPES = {"supplier", "customer", "project", "contract"}


@dataclass
class _Rule:
    event_type: str
    any_keywords: tuple[str, ...]
    require_entity_type: str | None = None
    forbid_entity_type: str | None = None
    forbid_keywords: tuple[str, ...] = ()
    direction: Direction | None = None  # None -> infer from text


# Ordered rules; the first matching rule per observation that also satisfies its
# entity requirement wins for that (event_type). Multiple distinct event types
# from one observation are allowed.
_RULES: tuple[_Rule, ...] = (
    _Rule(
        "supplier_price_change",
        ("price", "pricing", "tariff", "rate"),
        require_entity_type="supplier",
    ),
    _Rule(
        "customer_contraction",
        ("reduc", "declin", "churn", "cancel", "less", "cut", "down", "lower"),
        require_entity_type="customer",
    ),
    _Rule(
        "customer_expansion",
        ("expand", "increase", "more", "grow", "additional", "upsell"),
        require_entity_type="customer",
    ),
    _Rule(
        "project_delay", ("delay", "slip", "behind schedule", "late"), require_entity_type="project"
    ),
    _Rule(
        "cost_overrun",
        ("overrun", "over budget", "exceed budget", "exceeded budget", "above budget"),
    ),
    _Rule(
        "inventory_accumulation",
        ("inventory", "stock", "warehouse"),
        forbid_keywords=("shortage", "deplet", "stockout"),
    ),
    _Rule("inventory_shortage", ("shortage", "deplet", "stockout", "run out")),
    _Rule(
        "contract_obligation",
        ("obligation", "penalty", "payable", "owe", "committed", "minimum spend"),
    ),
    _Rule("payment_delay", ("overdue", "late payment", "pay late", "delayed payment", "arrears")),
    _Rule("capacity_change", ("capacity", "throughput", "utilization", "downtime")),
    # Generic price_change only when no supplier is named (else supplier_price_change wins).
    _Rule("price_change", ("price", "pricing", "tariff"), forbid_entity_type="supplier"),
)


@dataclass
class _Group:
    event_type: str
    direction: Direction
    entity_key: frozenset[str]
    observations: list[Observation] = field(default_factory=list)
    entity_refs: dict[str, EntityRef] = field(default_factory=dict)


class RuleBasedCandidateGenerator(EventCandidateGenerator):
    """Deterministic candidate generation from observations."""

    def __init__(self, organization_id: str | None = None) -> None:
        self.organization_id = organization_id

    def generate(self, observations: list[Observation]) -> list[EconomicEvent]:
        context_measurements = self._context_measurements(observations)
        groups: dict[tuple[str, str, frozenset[str]], _Group] = {}

        for obs in observations:
            text = self._obs_text(obs)
            matched = self._match_rules(obs, text)
            primary_keys = self._primary_entity_keys(obs)
            for event_type, direction in matched:
                key = (event_type, str(direction), primary_keys)
                group = groups.get(key)
                if group is None:
                    group = _Group(
                        event_type=event_type, direction=direction, entity_key=primary_keys
                    )
                    groups[key] = group
                group.observations.append(obs)
                for ref in obs.entities:
                    group.entity_refs[ref.entity_id] = ref

        candidates: list[EconomicEvent] = []
        for group in groups.values():
            candidates.append(self._build_event(group, context_measurements))
        return candidates

    # -- internals -----------------------------------------------------------
    def _match_rules(self, obs: Observation, text: str) -> list[tuple[str, Direction]]:
        low = text.lower()
        entity_types = {r.entity_type for r in obs.entities}
        results: list[tuple[str, Direction]] = []
        seen_types: set[str] = set()
        for rule in _RULES:
            if rule.event_type in seen_types:
                continue
            if rule.require_entity_type and rule.require_entity_type not in entity_types:
                continue
            if rule.forbid_entity_type and rule.forbid_entity_type in entity_types:
                continue
            if not any(kw in low for kw in rule.any_keywords):
                continue
            if any(kw in low for kw in rule.forbid_keywords):
                continue
            direction = rule.direction or self._direction_for(rule.event_type, low)
            results.append((rule.event_type, direction))
            seen_types.add(rule.event_type)
        return results

    def _direction_for(self, event_type: str, low: str) -> Direction:
        from .signals import infer_direction

        defn = EVENT_REGISTRY.try_get(event_type)
        inferred = infer_direction(low)
        if inferred in (Direction.INCREASE, Direction.DECREASE):
            return inferred
        if defn and defn.typical_direction != Direction.UNKNOWN:
            return Direction(defn.typical_direction)
        return Direction.UNKNOWN

    def _primary_entity_keys(self, obs: Observation) -> frozenset[str]:
        return frozenset(
            r.entity_id for r in obs.entities if r.entity_type in _PRIMARY_ENTITY_TYPES
        )

    def _context_measurements(self, observations: list[Observation]) -> list[Measurement]:
        pool: list[Measurement] = []
        for obs in observations:
            if not self._primary_entity_keys(obs):
                pool.extend(obs.measurements)
        return pool

    def _obs_text(self, obs: Observation) -> str:
        parts = [c.text for c in obs.claims]
        parts.extend(m.basis or "" for m in obs.measurements)
        return " \n".join(parts)

    def _build_event(self, group: _Group, context_measurements: list[Measurement]) -> EconomicEvent:
        obs_ids = sorted({o.id for o in group.observations})
        evidence_ids = sorted({e for o in group.observations for e in o.evidence_ids})
        effective_dates = [o.effective_at for o in group.observations if o.effective_at]
        effective_at = min(effective_dates) if effective_dates else None
        detected = min((o.observed_at for o in group.observations if o.observed_at), default=None)

        # Pool measurements: this group's own + shared context measurements.
        pooled: list[Measurement] = []
        for o in group.observations:
            pooled.extend(o.measurements)
        pooled.extend(context_measurements)

        magnitude, magnitude_unit = self._headline_magnitude(pooled)
        strength = max((o.confidence.score for o in group.observations), default=0.5)

        defn = EVENT_REGISTRY.try_get(group.event_type)
        provenance = Provenance(producer="RuleBasedCandidateGenerator")
        for o in group.observations:
            provenance = provenance.merge(o.provenance)

        event = EconomicEvent(
            event_type=group.event_type,
            title=self._title(group),
            organization_id=self.organization_id,
            status=EventStatus.EMERGING,
            entities=list(group.entity_refs.values()),
            observation_ids=obs_ids,
            evidence_ids=evidence_ids,
            effective_at=effective_at,
            magnitude=magnitude,
            magnitude_unit=magnitude_unit,
            confidence=Confidence(score=round(strength, 3), evidence_strength=strength),
            affected_metrics=list(defn.default_metrics) if defn else [],
            provenance=provenance,
        )
        if detected is not None:
            event.detected_at = detected
        return event

    def _headline_magnitude(
        self, measurements: list[Measurement]
    ) -> tuple[float | None, str | None]:
        for m in measurements:
            if m.name == "percent":
                return m.value, "percent"
        for m in measurements:
            if m.name == "money":
                return m.value, m.unit
        return None, None

    def _title(self, group: _Group) -> str:
        names = [
            ref.name
            for ref in group.entity_refs.values()
            if ref.entity_type in _PRIMARY_ENTITY_TYPES
        ]
        subject = names[0] if names else "unspecified"
        label = EVENT_REGISTRY.try_get(group.event_type)
        return f"{label.label if label else group.event_type}: {subject}"
