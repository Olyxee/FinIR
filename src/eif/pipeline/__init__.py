"""The multimodal reasoning pipeline and its replaceable stages."""

from __future__ import annotations

from .candidate import RuleBasedCandidateGenerator
from .extractor import DeterministicObservationExtractor, LLMObservationExtractor
from .impact import DeterministicImpactEstimator, pool_measurements
from .materiality import ThresholdMaterialityEngine
from .pipeline import EIFPipeline, PipelineResult
from .stages import (
    EventCandidateGenerator,
    ImpactEstimator,
    MaterialityDecision,
    MaterialityEngine,
    ObservationExtractor,
)

__all__ = [
    "EIFPipeline",
    "PipelineResult",
    # stage interfaces
    "ObservationExtractor",
    "EventCandidateGenerator",
    "ImpactEstimator",
    "MaterialityEngine",
    "MaterialityDecision",
    # default implementations
    "DeterministicObservationExtractor",
    "LLMObservationExtractor",
    "RuleBasedCandidateGenerator",
    "DeterministicImpactEstimator",
    "ThresholdMaterialityEngine",
    "pool_measurements",
]
