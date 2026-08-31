"""Enumerations for the EIF domain model.

These enums cover the *closed* vocabularies of the framework. Deliberately
*open* vocabularies — economic event types, entity types, affected metrics — are
handled by the extensible registries in :mod:`eif.ontology`, not by enums, so
that downstream users can add their own without patching the framework.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String-valued enum that serializes to its value and compares to str."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class Modality(StrEnum):
    """The high-level modality of a piece of evidence."""

    TEXT = "text"
    EMAIL = "email"
    DOCUMENT = "document"  # PDF / Word / etc.
    TABLE = "table"  # CSV / Excel / db rows
    JSON = "json"
    TRANSCRIPT = "transcript"  # call / meeting transcript
    AUDIO = "audio"
    IMAGE = "image"
    TIMESERIES = "timeseries"
    API = "api"


class SourceType(StrEnum):
    """Where a piece of evidence originated."""

    FILE = "file"
    EMAIL = "email"
    CHAT = "chat"  # Slack / Teams
    CRM = "crm"
    ERP = "erp"
    DATABASE = "database"
    API = "api"
    UPLOAD = "upload"
    STREAM = "stream"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class ExtractionMethod(StrEnum):
    """How a derived object (observation/event/impact) was produced."""

    DETERMINISTIC = "deterministic"  # pure code, no model
    RULE = "rule"  # rule/heuristic engine
    LLM = "llm"  # language model
    VISION = "vision"  # vision model
    HYBRID = "hybrid"  # deterministic + model
    HUMAN = "human"  # human-authored / corrected


class EventStatus(StrEnum):
    """Lifecycle status of an economic event in the graph."""

    EMERGING = "emerging"  # first detected, still forming
    CONFIRMED = "confirmed"  # reinforced by additional evidence
    WEAKENED = "weakened"  # contradicting evidence reduced confidence
    RESOLVED = "resolved"  # played out; outcome known
    DISMISSED = "dismissed"  # judged false / immaterial and closed
    SUPERSEDED = "superseded"  # replaced by a split/merged event


class Direction(StrEnum):
    """Direction of a change or impact on a metric."""

    INCREASE = "increase"
    DECREASE = "decrease"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class Materiality(StrEnum):
    """Materiality classification assigned by the materiality engine."""

    MATERIAL = "material"
    NON_MATERIAL = "non_material"
    UNKNOWN = "unknown"


class RelationshipType(StrEnum):
    """Typed edges between economic events (and, where useful, entities)."""

    CAUSES = "causes"
    CONTRIBUTES_TO = "contributes_to"
    AFFECTS = "affects"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    MITIGATES = "mitigates"
    AMPLIFIES = "amplifies"
    PRECEDES = "precedes"
    RESOLVES = "resolves"
    DERIVED_FROM = "derived_from"


class EvidenceStance(StrEnum):
    """Whether a piece of evidence supports or contradicts a claim/event."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
