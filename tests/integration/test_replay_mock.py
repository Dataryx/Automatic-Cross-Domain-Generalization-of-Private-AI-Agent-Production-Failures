"""Replay mock service integration test."""

from fastapi.testclient import TestClient

from cfi_contributor.graph import GraphEdge, IncidentGraph, RelationClass
from cfi_contributor.replay import HttpAgentReplayProvider
from cfi_core.models import ProvenanceClass
from services.integrations.replay.main import app


def test_replay_mock_server_and_http_provider() -> None:
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"

    graph = IncidentGraph(
        nodes={"e0": {"event": "action"}},
        edges=[
            GraphEdge(
                source="e0",
                target="e1",
                relation=RelationClass.POLICY_FLOW,
                provenance=ProvenanceClass.OBSERVED,
            )
        ],
    )
    provider = HttpAgentReplayProvider("http://testserver/replay")
    provider._call = lambda g, seed: client.post(  # type: ignore[method-assign]
        "/replay",
        json={
            "nodes": g.nodes,
            "edges": [{"source": e.source, "target": e.target, "relation": e.relation.value} for e in g.edges],
            "seed": seed,
        },
    ).json().get("failure_rate", 0.0)
    ev = provider.estimate_failure_rate(graph, trials=1, seed=0)
    assert ev.failure_rate == 1.0

    graph.nodes["e0"]["intervention"] = "insert_verification"
    ev2 = provider.estimate_failure_rate(graph, trials=1, seed=0)
    assert ev2.failure_rate == 0.0
