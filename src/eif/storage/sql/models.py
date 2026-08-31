"""SQLAlchemy ORM models.

EIF uses a *document-in-relational* layout: the full domain object is stored as
JSON in a ``payload`` column, with a handful of extracted, indexed columns for
the fields we filter and sort on. Benefits:

* Identical schema and behavior on SQLite and PostgreSQL (portable ``JSON`` type).
* No brittle ORM mapping of deeply nested Pydantic models; the domain model stays
  the single source of truth for shape and validation.
* Round-trips are loss-less: ``Model.model_validate(row.payload)`` reconstructs
  the exact object.

Timestamps used for range filters are stored as sortable ISO-8601 strings so
lexicographic comparison works uniformly across backends.
"""

from __future__ import annotations

from sqlalchemy import JSON, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EvidenceRow(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    modality: Mapped[str] = mapped_column(String(32), index=True)
    content_hash: Mapped[str | None] = mapped_column(String(80), index=True)
    ingested_at_iso: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ObservationRow(Base):
    __tablename__ = "observations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_iso: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class EntityRow(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    materiality: Mapped[str] = mapped_column(String(32), index=True)
    detected_at_iso: Mapped[str] = mapped_column(String(40), index=True)
    entity_ids_csv: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON)


class RelationshipRow(Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_event_id: Mapped[str] = mapped_column(String(64), index=True)
    target_event_id: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class OutcomeRow(Base):
    __tablename__ = "outcomes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    recorded_iso: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


# Composite index that speeds the most common event query (org + type + time).
Index(
    "ix_events_org_type_time",
    EventRow.organization_id,
    EventRow.event_type,
    EventRow.detected_at_iso,
)
