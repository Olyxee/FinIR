"""The multimodal reasoning pipeline orchestrator.

Wires the replaceable stages together and drives evidence through:

    persist evidence -> extract observations -> resolve entities
    -> generate candidates -> estimate impacts -> assess materiality
    -> integrate into the event graph (event resolution + persistence)

Each stage is injectable, so callers can replace the observation extractor,
candidate generator, impact estimator, materiality engine, or resolvers::

    pipeline = EIFPipeline(
        repo,
        observation_extractor=my_extractor,
        impact_estimator=my_estimator,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..domain import (
    EconomicEntity,
    EconomicEvent,
    EntityRef,
    Evidence,
    Observation,
)
from ..graph import EventGraph
from ..graph.resolution import DefaultEntityResolver, EntityResolver
from ..logging import get_logger, stage_timer
from ..storage.base import Repository
from ..utils.ids import new_id
from .candidate import RuleBasedCandidateGenerator
from .extractor import DeterministicObservationExtractor
from .impact import DeterministicImpactEstimator
from .materiality import ThresholdMaterialityEngine
from .stages import (
    EventCandidateGenerator,
    ImpactEstimator,
    MaterialityEngine,
    ObservationExtractor,
)


@dataclass
class PipelineResult:
    """Everything produced by one pipeline run."""

    run_id: str
    evidence: list[Evidence] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    events: list[EconomicEvent] = field(default_factory=list)
    integrations: list[tuple[str, str]] = field(default_factory=list)  # (event_id, action)

    def material_events(self) -> list[EconomicEvent]:
        return [e for e in self.events if e.is_material()]


class EIFPipeline:
    """Composable multimodal reasoning pipeline."""

    def __init__(
        self,
        repo: Repository,
        *,
        config: Config | None = None,
        observation_extractor: ObservationExtractor | None = None,
        candidate_generator: EventCandidateGenerator | None = None,
        impact_estimator: ImpactEstimator | None = None,
        materiality_engine: MaterialityEngine | None = None,
        entity_resolver: EntityResolver | None = None,
        graph: EventGraph | None = None,
    ) -> None:
        self.repo = repo
        self.config = config or Config()
        org = self.config.organization.id
        self.observation_extractor = observation_extractor or DeterministicObservationExtractor()
        self.candidate_generator = candidate_generator or RuleBasedCandidateGenerator(org)
        self.impact_estimator = impact_estimator or DeterministicImpactEstimator(
            self.config.organization.currency
        )
        self.materiality_engine = materiality_engine or ThresholdMaterialityEngine(
            self.config.materiality
        )
        self.entity_resolver = entity_resolver or DefaultEntityResolver()
        self.graph = graph or EventGraph(repo, entity_resolver=self.entity_resolver)
        self.log = get_logger("pipeline", organization_id=org)

    def process_evidence(self, evidence_list: list[Evidence]) -> PipelineResult:
        run_id = new_id("run")
        log = get_logger("pipeline", run_id=run_id, organization_id=self.config.organization.id)
        result = PipelineResult(run_id=run_id)

        # 1. Persist evidence.
        with stage_timer(log, "persist_evidence", count=len(evidence_list)):
            for ev in evidence_list:
                if ev.security.organization_id is None:
                    ev.security.organization_id = self.config.organization.id
                self.repo.add_evidence(ev)
                result.evidence.append(ev)

        # 2. Extract observations.
        observations: list[Observation] = []
        with stage_timer(log, "extract_observations"):
            for ev in evidence_list:
                observations.extend(self.observation_extractor.extract(ev))

        # 3. Resolve entities and rewrite references to canonical ids.
        with stage_timer(log, "resolve_entities", observations=len(observations)):
            id_map = self._resolve_entities(observations)
            for obs in observations:
                obs.entities = [self._remap_ref(ref, id_map) for ref in obs.entities]

        # 4. Persist observations.
        for obs in observations:
            self.repo.add_observation(obs)
        result.observations = observations

        # 5. Candidate generation.
        with stage_timer(log, "generate_candidates"):
            candidates = self.candidate_generator.generate(observations)

        # 6-8. Impact, materiality, integrate.
        with stage_timer(log, "impact_materiality_integrate", candidates=len(candidates)):
            for candidate in candidates:
                candidate.organization_id = candidate.organization_id or self.config.organization.id
                impacts = self.impact_estimator.estimate(candidate, observations)
                candidate.impacts = impacts
                candidate.affected_metrics = sorted(
                    {*candidate.affected_metrics, *(i.metric for i in impacts)}
                )
                decision = self.materiality_engine.assess(candidate)
                candidate.materiality = decision.materiality
                candidate.provenance.notes.append(f"materiality: {decision.reason}")

                integration = self.graph.integrate(candidate)
                result.events.append(integration.event)
                result.integrations.append((integration.event.id, integration.action))
                log.info(
                    "event.integrated",
                    extra={
                        "event_id": integration.event.id,
                        "event_type": integration.event.event_type,
                        "action": integration.action,
                        "materiality": str(integration.event.materiality),
                    },
                )

        return result

    # -- entity resolution helpers ------------------------------------------
    def _resolve_entities(self, observations: list[Observation]) -> dict[str, EntityRef]:
        id_map: dict[str, EntityRef] = {}
        for obs in observations:
            for ref in obs.entities:
                if ref.entity_id in id_map:
                    continue
                entity = EconomicEntity(
                    entity_type=ref.entity_type,
                    name=ref.name,
                    organization_id=self.config.organization.id,
                )
                resolution = self.entity_resolver.resolve(entity, self.repo)
                canonical = resolution.entity
                id_map[ref.entity_id] = EntityRef(
                    entity_id=canonical.id,
                    entity_type=canonical.entity_type,
                    name=canonical.name,
                    role=ref.role,
                )
        return id_map

    @staticmethod
    def _remap_ref(ref: EntityRef, id_map: dict[str, EntityRef]) -> EntityRef:
        mapped = id_map.get(ref.entity_id)
        if mapped is None:
            return ref
        return EntityRef(
            entity_id=mapped.entity_id,
            entity_type=mapped.entity_type,
            name=mapped.name,
            role=ref.role,
        )
