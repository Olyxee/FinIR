"""SQLAlchemy implementation of the EIF :class:`Repository` interface."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ...domain import (
    EconomicEntity,
    EconomicEvent,
    EventRelationship,
    Evidence,
    Observation,
    RealizedOutcome,
)
from ...exceptions import StorageError
from ..base import (
    EntityQuery,
    EventQuery,
    Page,
    Repository,
    RepositoryStats,
)
from .models import (
    Base,
    EntityRow,
    EventRow,
    EvidenceRow,
    ObservationRow,
    OutcomeRow,
    RelationshipRow,
)


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.min).isoformat()


class SqlRepository(Repository):
    """Persistent repository backed by any SQLAlchemy-supported database."""

    def __init__(self, database_url: str = "sqlite:///./eif.db", *, echo: bool = False) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        try:
            self._engine: Engine = create_engine(
                database_url, echo=echo, future=True, connect_args=connect_args
            )
        except Exception as exc:
            raise StorageError(f"Could not create engine for {database_url!r}: {exc}") from exc
        self._Session = sessionmaker(bind=self._engine, future=True, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        return self._engine

    def init_schema(self) -> None:
        Base.metadata.create_all(self._engine)

    def close(self) -> None:
        self._engine.dispose()

    # -- evidence ------------------------------------------------------------
    def add_evidence(self, evidence: Evidence) -> Evidence:
        with self._session() as s:
            s.merge(
                EvidenceRow(
                    id=evidence.id,
                    organization_id=evidence.security.organization_id,
                    source_type=str(evidence.source_type),
                    modality=str(evidence.modality),
                    content_hash=evidence.content_hash,
                    ingested_at_iso=_iso(evidence.ingested_at),
                    payload=evidence.model_dump(mode="json"),
                )
            )
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        with self._session() as s:
            row = s.get(EvidenceRow, evidence_id)
            return Evidence.model_validate(row.payload) if row else None

    def list_evidence(self, *, limit: int = 50, offset: int = 0) -> Page[Evidence]:
        with self._session() as s:
            total = s.scalar(select(func.count()).select_from(EvidenceRow)) or 0
            rows = s.scalars(
                select(EvidenceRow)
                .order_by(EvidenceRow.ingested_at_iso.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            items = [Evidence.model_validate(r.payload) for r in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)

    # -- observations --------------------------------------------------------
    def add_observation(self, observation: Observation) -> Observation:
        with self._session() as s:
            s.merge(
                ObservationRow(
                    id=observation.id,
                    created_iso=_iso(observation.observed_at),
                    payload=observation.model_dump(mode="json"),
                )
            )
        return observation

    def get_observation(self, observation_id: str) -> Observation | None:
        with self._session() as s:
            row = s.get(ObservationRow, observation_id)
            return Observation.model_validate(row.payload) if row else None

    def list_observations(self, *, limit: int = 50, offset: int = 0) -> Page[Observation]:
        with self._session() as s:
            total = s.scalar(select(func.count()).select_from(ObservationRow)) or 0
            rows = s.scalars(select(ObservationRow).limit(limit).offset(offset)).all()
            items = [Observation.model_validate(r.payload) for r in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)

    # -- entities ------------------------------------------------------------
    def upsert_entity(self, entity: EconomicEntity) -> EconomicEntity:
        key = entity.dedup_key()
        with self._session() as s:
            existing = s.scalar(select(EntityRow).where(EntityRow.dedup_key == key))
            if existing is not None:
                current = EconomicEntity.model_validate(existing.payload)
                current.aliases = sorted(
                    {*current.aliases, *entity.aliases, entity.name} - {current.name}
                )
                current.external_ids = {**current.external_ids, **entity.external_ids}
                current.attributes = {**current.attributes, **entity.attributes}
                existing.payload = current.model_dump(mode="json")
                return current
            s.add(
                EntityRow(
                    id=entity.id,
                    dedup_key=key,
                    organization_id=entity.organization_id,
                    entity_type=entity.entity_type,
                    name=entity.name,
                    payload=entity.model_dump(mode="json"),
                )
            )
        return entity

    def get_entity(self, entity_id: str) -> EconomicEntity | None:
        with self._session() as s:
            row = s.get(EntityRow, entity_id)
            return EconomicEntity.model_validate(row.payload) if row else None

    def find_entity_by_key(self, dedup_key: str) -> EconomicEntity | None:
        with self._session() as s:
            row = s.scalar(select(EntityRow).where(EntityRow.dedup_key == dedup_key))
            return EconomicEntity.model_validate(row.payload) if row else None

    def list_entities(self, query: EntityQuery | None = None) -> Page[EconomicEntity]:
        q = query or EntityQuery()
        with self._session() as s:
            stmt = select(EntityRow)
            count_stmt = select(func.count()).select_from(EntityRow)
            if q.organization_id is not None:
                stmt = stmt.where(EntityRow.organization_id == q.organization_id)
                count_stmt = count_stmt.where(EntityRow.organization_id == q.organization_id)
            if q.entity_type is not None:
                stmt = stmt.where(EntityRow.entity_type == q.entity_type)
                count_stmt = count_stmt.where(EntityRow.entity_type == q.entity_type)
            total = s.scalar(count_stmt) or 0
            rows = s.scalars(stmt.limit(q.limit).offset(q.offset)).all()
            items = [EconomicEntity.model_validate(r.payload) for r in rows]
        return Page(items=items, total=total, limit=q.limit, offset=q.offset)

    # -- events --------------------------------------------------------------
    def add_event(self, event: EconomicEvent) -> EconomicEvent:
        return self._save_event(event)

    def update_event(self, event: EconomicEvent) -> EconomicEvent:
        return self._save_event(event)

    def _save_event(self, event: EconomicEvent) -> EconomicEvent:
        with self._session() as s:
            s.merge(
                EventRow(
                    id=event.id,
                    organization_id=event.organization_id,
                    event_type=event.event_type,
                    status=str(event.status),
                    materiality=str(event.materiality),
                    detected_at_iso=_iso(event.detected_at),
                    entity_ids_csv=",".join(event.entity_ids()),
                    payload=event.model_dump(mode="json"),
                )
            )
        return event

    def get_event(self, event_id: str) -> EconomicEvent | None:
        with self._session() as s:
            row = s.get(EventRow, event_id)
            return EconomicEvent.model_validate(row.payload) if row else None

    def list_events(self, query: EventQuery | None = None) -> Page[EconomicEvent]:
        q = query or EventQuery()
        with self._session() as s:
            stmt = select(EventRow)
            count_stmt = select(func.count()).select_from(EventRow)

            def apply(base):
                if q.organization_id is not None:
                    base = base.where(EventRow.organization_id == q.organization_id)
                if q.event_type is not None:
                    base = base.where(EventRow.event_type == q.event_type)
                if q.status is not None:
                    base = base.where(EventRow.status == q.status)
                if q.materiality is not None:
                    base = base.where(EventRow.materiality == q.materiality)
                if q.entity_id is not None:
                    base = base.where(EventRow.entity_ids_csv.contains(q.entity_id))
                if q.detected_after is not None:
                    base = base.where(EventRow.detected_at_iso >= _iso(q.detected_after))
                if q.detected_before is not None:
                    base = base.where(EventRow.detected_at_iso <= _iso(q.detected_before))
                return base

            total = s.scalar(apply(count_stmt)) or 0
            order = (
                EventRow.detected_at_iso.desc() if q.order_desc else EventRow.detected_at_iso.asc()
            )
            rows = s.scalars(apply(stmt).order_by(order).limit(q.limit).offset(q.offset)).all()
            items = [EconomicEvent.model_validate(r.payload) for r in rows]
        return Page(items=items, total=total, limit=q.limit, offset=q.offset)

    # -- relationships -------------------------------------------------------
    def add_relationship(self, relationship: EventRelationship) -> EventRelationship:
        with self._session() as s:
            s.merge(
                RelationshipRow(
                    id=relationship.id,
                    source_event_id=relationship.source_event_id,
                    target_event_id=relationship.target_event_id,
                    type=str(relationship.type),
                    payload=relationship.model_dump(mode="json"),
                )
            )
        return relationship

    def list_relationships(self, *, event_id: str | None = None) -> list[EventRelationship]:
        with self._session() as s:
            stmt = select(RelationshipRow)
            if event_id is not None:
                stmt = stmt.where(
                    (RelationshipRow.source_event_id == event_id)
                    | (RelationshipRow.target_event_id == event_id)
                )
            rows = s.scalars(stmt).all()
            return [EventRelationship.model_validate(r.payload) for r in rows]

    # -- outcomes ------------------------------------------------------------
    def add_outcome(self, outcome: RealizedOutcome) -> RealizedOutcome:
        with self._session() as s:
            s.merge(
                OutcomeRow(
                    id=outcome.id,
                    event_id=outcome.event_id,
                    recorded_iso=_iso(outcome.recorded_at),
                    payload=outcome.model_dump(mode="json"),
                )
            )
        return outcome

    def get_outcome_for_event(self, event_id: str) -> RealizedOutcome | None:
        with self._session() as s:
            row = s.scalar(
                select(OutcomeRow)
                .where(OutcomeRow.event_id == event_id)
                .order_by(OutcomeRow.recorded_iso.desc())
            )
            return RealizedOutcome.model_validate(row.payload) if row else None

    def list_outcomes(self, *, limit: int = 50, offset: int = 0) -> Page[RealizedOutcome]:
        with self._session() as s:
            total = s.scalar(select(func.count()).select_from(OutcomeRow)) or 0
            rows = s.scalars(
                select(OutcomeRow)
                .order_by(OutcomeRow.recorded_iso.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            items = [RealizedOutcome.model_validate(r.payload) for r in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)

    # -- stats ---------------------------------------------------------------
    def stats(self) -> RepositoryStats:
        with self._session() as s:
            return RepositoryStats(
                evidence=s.scalar(select(func.count()).select_from(EvidenceRow)) or 0,
                observations=s.scalar(select(func.count()).select_from(ObservationRow)) or 0,
                entities=s.scalar(select(func.count()).select_from(EntityRow)) or 0,
                events=s.scalar(select(func.count()).select_from(EventRow)) or 0,
                relationships=s.scalar(select(func.count()).select_from(RelationshipRow)) or 0,
                outcomes=s.scalar(select(func.count()).select_from(OutcomeRow)) or 0,
            )

    # -- internals -----------------------------------------------------------
    def _session(self) -> _SessionCtx:
        return _SessionCtx(self._Session)


class _SessionCtx:
    """Context manager committing on success and rolling back on error."""

    def __init__(self, factory: sessionmaker) -> None:
        self._factory = factory
        self._session: Session | None = None

    def __enter__(self) -> Session:
        self._session = self._factory()
        return self._session

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()
