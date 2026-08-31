"""Pipeline stage interfaces.

Each stage of the multimodal reasoning pipeline is a small, replaceable
component behind an abstract interface, so developers can swap any one out::

    Connector -> Parser -> ObservationExtractor -> EntityResolution
        -> EventCandidateGenerator -> EventResolution -> ImpactEstimator
        -> MaterialityFilter -> Persistence -> Evaluation
"""

from __future__ import annotations

import abc

from ..domain import EconomicEvent, EconomicImpact, Evidence, Observation
from ..domain.enums import Materiality


class ObservationExtractor(abc.ABC):
    """Turns a single Evidence into zero or more structured Observations."""

    @abc.abstractmethod
    def extract(self, evidence: Evidence) -> list[Observation]: ...


class EventCandidateGenerator(abc.ABC):
    """Turns a set of observations into candidate (pre-impact) events."""

    @abc.abstractmethod
    def generate(self, observations: list[Observation]) -> list[EconomicEvent]: ...


class ImpactEstimator(abc.ABC):
    """Attaches deterministic financial impact estimates to an event."""

    @abc.abstractmethod
    def estimate(
        self, event: EconomicEvent, observations: list[Observation]
    ) -> list[EconomicImpact]: ...


class MaterialityDecision:
    """Result of a materiality assessment."""

    def __init__(self, materiality: Materiality, reason: str) -> None:
        self.materiality = materiality
        self.reason = reason


class MaterialityEngine(abc.ABC):
    """Classifies an event as material / non-material given configured thresholds."""

    @abc.abstractmethod
    def assess(self, event: EconomicEvent) -> MaterialityDecision: ...
