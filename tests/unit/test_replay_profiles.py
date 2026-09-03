"""Replay profile resolution tests."""

import os

import pytest

from cfi_contributor.replay import HttpAgentReplayProvider, StructuralReplayProvider
from cfi_contributor.replay_profiles import REPLAY_PROFILES, list_profiles, resolve_replay_provider


def test_list_profiles_includes_production_hooks() -> None:
    names = list_profiles()
    assert "mock" in names
    assert "agentrx" in names
    assert "causalflow" in names


def test_resolve_structural_by_default() -> None:
    provider = resolve_replay_provider()
    assert isinstance(provider, StructuralReplayProvider)


def test_resolve_explicit_url() -> None:
    provider = resolve_replay_provider(replay_url="http://example/replay")
    assert isinstance(provider, HttpAgentReplayProvider)


def test_resolve_mock_profile_against_replay_service(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from cfi_contributor.graph import GraphEdge, IncidentGraph, RelationClass
    from cfi_contributor.replay import HttpAgentReplayProvider
    from cfi_core.models import ProvenanceClass
    from services.integrations.replay.main import app as replay_app

    client = TestClient(replay_app)
    monkeypatch.setenv("CFI_REPLAY_MOCK_URL", "http://testserver/replay")

    class _Client:
        def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
            return client.post("/replay", json=json)

    provider = HttpAgentReplayProvider(os.environ["CFI_REPLAY_MOCK_URL"], client=_Client())

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
    ev = provider.estimate_failure_rate(graph, trials=1, seed=0)
    assert ev.failure_rate == 1.0


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError, match="Unknown replay profile"):
        resolve_replay_provider(replay_profile="not-a-profile")


def test_profile_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CFI_AGENTRX_URL", "http://agentrx.local/v1/replay")
    provider = resolve_replay_provider(replay_profile="agentrx")
    assert isinstance(provider, HttpAgentReplayProvider)
    assert provider._endpoint == "http://agentrx.local/v1/replay"
    assert REPLAY_PROFILES["agentrx"].endpoint_env == "CFI_AGENTRX_URL"
