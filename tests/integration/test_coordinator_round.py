"""Coordinator consortium round test."""

from fastapi.testclient import TestClient

from services.coordinator.main import app


def test_coordinator_consortium_round() -> None:
    client = TestClient(app)
    resp = client.post("/consortium/round", json={"tenants": 10, "minimum_k": 10, "seed": 421337})
    assert resp.status_code == 200
    body = resp.json()
    assert body["released"] is True
    assert body["participants"] >= 10
