"""API tests using FastAPI TestClient over an in-memory EIF."""

from __future__ import annotations

import pytest

from eif.config import Config
from eif.facade import EIF

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from eif.api.app import create_app  # noqa: E402


@pytest.fixture
def client():
    cfg = Config()
    cfg.storage.database_url = "memory"
    cfg.logging.level = "ERROR"
    return TestClient(create_app(EIF(cfg)))


def test_health_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"


def test_analyze_and_list(client):
    r = client.post(
        "/v1/analyze",
        json={"texts": ["Supplier ABC will raise prices 10% on SKU-A. Annual spend R42,000,000."]},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) >= 1
    ev = body["events"][0]
    assert ev["event_type"] == "supplier_price_change"

    listing = client.get("/v1/events?limit=10").json()
    assert listing["total"] >= 1
    assert "has_more" in listing


def test_get_event_and_404(client):
    ev = client.post(
        "/v1/analyze", json={"texts": ["Supplier ABC raises prices 10%. Spend R42,000,000."]}
    ).json()["events"][0]
    assert client.get(f"/v1/events/{ev['id']}").status_code == 200
    missing = client.get("/v1/events/nope")
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"


def test_outcome_and_metrics(client):
    ev = client.post(
        "/v1/analyze", json={"texts": ["Supplier ABC raises prices 10%. Spend R42,000,000."]}
    ).json()["events"][0]
    r = client.post(
        "/v1/outcomes",
        json={
            "event_id": ev["id"],
            "realized_metrics": {"cost_of_goods_sold": 3_980_000},
            "traditional_detected_at": "2026-10-21",
        },
    )
    assert r.status_code == 200
    metrics = client.get("/v1/metrics").json()
    assert metrics["counts"]["events"] >= 1
    assert metrics["eslt"]["n"] >= 1


def test_post_evidence(client):
    r = client.post("/v1/evidence", json={"source": "api", "content": "hello", "modality": "text"})
    assert r.status_code == 200
    assert r.json()["content_hash"].startswith("sha256:")


def test_openapi_available(client):
    spec = client.get("/openapi.json").json()
    assert "/v1/analyze" in spec["paths"]
