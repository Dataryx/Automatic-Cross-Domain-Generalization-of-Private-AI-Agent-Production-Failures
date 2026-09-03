#!/usr/bin/env python3
"""Verify mock, AgentRx, and CausalFlow replay profile stubs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.graph import IncidentGraph
from cfi_contributor.replay import HttpAgentReplayProvider
from cfi_contributor.replay_profiles import REPLAY_PROFILES, resolve_replay_provider
from services.integrations.agentrx.main import app as agentrx_app
from services.integrations.causalflow.main import app as causalflow_app
from services.integrations.replay.main import app as replay_mock_app


class _InProcessReplayClient:
    def __init__(self, test_client: TestClient, path: str) -> None:
        self._client = test_client
        self._path = path

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post(self._path, json=json)


def _sample_graph() -> IncidentGraph:
    return IncidentGraph()


def _check_profile(name: str, app: object, path: str) -> tuple[bool, str]:
    client = TestClient(app)
    health = client.get("/health")
    if health.status_code != 200:
        return False, f"{name} health failed: {health.status_code}"
    provider = HttpAgentReplayProvider(
        REPLAY_PROFILES[name].default_url,
        client=_InProcessReplayClient(client, path),
    )
    evidence = provider.estimate_failure_rate(_sample_graph(), trials=2, seed=421337)
    if evidence.failure_rate < 0.0 or evidence.failure_rate > 1.0:
        return False, f"{name} invalid failure_rate={evidence.failure_rate}"
    resolved = resolve_replay_provider(replay_profile=name)
    if resolved._endpoint != REPLAY_PROFILES[name].default_url:
        return False, f"{name} profile resolution mismatch"
    return True, f"{name} failure_rate={evidence.failure_rate}"


def main() -> int:
    checks = [
        ("mock", replay_mock_app, "/replay"),
        ("agentrx", agentrx_app, "/v1/replay"),
        ("causalflow", causalflow_app, "/v1/counterfactual"),
    ]
    failed = False
    for name, app, path in checks:
        ok, message = _check_profile(name, app, path)
        print(f"[{'PASS' if ok else 'FAIL'}] {message}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
