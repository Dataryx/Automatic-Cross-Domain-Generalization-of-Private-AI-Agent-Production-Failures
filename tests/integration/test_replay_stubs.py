"""Replay stub service tests."""

from fastapi.testclient import TestClient

from services.integrations.agentrx.main import app as agentrx_app
from services.integrations.causalflow.main import app as causalflow_app
from services.integrations.replay.main import app as replay_mock_app


def test_agentrx_stub_returns_diagnostic_id() -> None:
    client = TestClient(agentrx_app)
    resp = client.post(
        "/v1/replay",
        json={"nodes": {"n1": {}}, "edges": [{"source": "a", "target": "b", "relation": "policy_flow"}], "seed": 7},
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["failure_rate"] == 1.0
    assert data["diagnostic_id"] == "arx-7"


def test_causalflow_stub_returns_counterfactual_id() -> None:
    client = TestClient(causalflow_app)
    resp = client.post(
        "/v1/counterfactual",
        json={"nodes": {"n1": {"intervention": "enforce_precedence"}}, "edges": [], "seed": 3},
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["failure_rate"] == 0.0
    assert data["counterfactual_run_id"] == "cf-3"


def test_replay_mock_health() -> None:
    client = TestClient(replay_mock_app)
    assert client.get("/health").status_code == 200
