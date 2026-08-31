"""Persistence tests across both backends (parametrized)."""

from __future__ import annotations

import pytest

from eif.domain import (
    Confidence,
    EconomicEntity,
    EconomicEvent,
    EntityRef,
    Evidence,
    RealizedOutcome,
)
from eif.storage import open_repository
from eif.storage.base import EventQuery


@pytest.fixture(params=["memory", "sql"])
def repo(request, tmp_path):
    if request.param == "memory":
        r = open_repository("memory")
    else:
        r = open_repository(f"sqlite:///{tmp_path / 'test.db'}")
    yield r
    close = getattr(r, "close", None)
    if callable(close):
        close()


def test_evidence_roundtrip(repo):
    ev = Evidence(source="e", content="hello")
    repo.add_evidence(ev)
    got = repo.get_evidence(ev.id)
    assert got is not None and got.content == "hello"


def test_entity_dedup(repo):
    a = EconomicEntity(entity_type="supplier", name="ABC", organization_id="o")
    b = EconomicEntity(entity_type="supplier", name="ABC", aliases=["ABC Ltd"], organization_id="o")
    r1 = repo.upsert_entity(a)
    r2 = repo.upsert_entity(b)
    assert r1.id == r2.id
    assert repo.stats().entities == 1
    assert "ABC Ltd" in repo.get_entity(r1.id).aliases


def test_event_crud_and_filter(repo):
    ref = EntityRef(entity_id="en_1", entity_type="supplier", name="ABC")
    ev = EconomicEvent(
        event_type="supplier_price_change",
        organization_id="o",
        entities=[ref],
        confidence=Confidence(score=0.8),
    )
    repo.add_event(ev)
    assert repo.get_event(ev.id).event_type == "supplier_price_change"

    page = repo.list_events(EventQuery(event_type="supplier_price_change"))
    assert page.total == 1
    assert repo.list_events(EventQuery(event_type="nope")).total == 0
    assert repo.list_events(EventQuery(entity_id="en_1")).total == 1


def test_event_update_persists(repo):
    ev = EconomicEvent(event_type="price_change")
    repo.add_event(ev)
    ev.title = "changed"
    ev.touch()
    repo.update_event(ev)
    assert repo.get_event(ev.id).title == "changed"


def test_pagination(repo):
    for _ in range(5):
        repo.add_event(EconomicEvent(event_type="price_change", organization_id="o"))
    page = repo.list_events(EventQuery(limit=2, offset=0))
    assert len(page.items) == 2 and page.total == 5 and page.has_more


def test_outcome_roundtrip(repo):
    ev = EconomicEvent(event_type="price_change")
    repo.add_event(ev)
    outcome = RealizedOutcome(event_id=ev.id, realized_metrics={"revenue": 100})
    repo.add_outcome(outcome)
    got = repo.get_outcome_for_event(ev.id)
    assert got is not None and got.realized_metrics["revenue"] == 100


def test_memory_isolation(repo):
    ev = EconomicEvent(event_type="price_change", title="orig")
    repo.add_event(ev)
    ev.title = "mutated-after-store"  # must not affect stored copy
    assert repo.get_event(ev.id).title == "orig"
