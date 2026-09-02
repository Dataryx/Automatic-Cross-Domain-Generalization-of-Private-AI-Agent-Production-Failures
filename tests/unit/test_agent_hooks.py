"""Agent hook probe tests."""

from fastapi.testclient import TestClient

from cfi_contributor.agent_hooks import PROFILE_PATHS, probe_replay_profile
from services.agentrx_stub.main import app as agentrx_app


class _InProcessReplayClient:
    def __init__(self, test_client: TestClient, path: str) -> None:
        self._client = test_client
        self._path = path

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post(self._path, json=json)


def test_probe_agentrx_hook() -> None:
    client = TestClient(agentrx_app)
    result = probe_replay_profile(
        "agentrx",
        health_client=client,
        replay_client=_InProcessReplayClient(client, PROFILE_PATHS["agentrx"]),
    )
    assert result.healthy
    assert result.replay_ok
    assert result.failure_rate is not None
