#!/usr/bin/env python3
"""Verify AgentRx/CausalFlow/mock replay hook health and replay responses."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.agent_hooks import PROFILE_PATHS, probe_replay_profile
from services.integrations.agentrx.main import app as agentrx_app
from services.integrations.causalflow.main import app as causalflow_app
from services.integrations.replay.main import app as replay_mock_app


class _InProcessReplayClient:
    def __init__(self, test_client: TestClient, path: str) -> None:
        self._client = test_client
        self._path = path

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post(self._path, json=json)


def main() -> int:
    checks = [
        ("mock", replay_mock_app),
        ("agentrx", agentrx_app),
        ("causalflow", causalflow_app),
    ]
    failed = False
    for name, app in checks:
        client = TestClient(app)
        result = probe_replay_profile(
            name,
            health_client=client,
            replay_client=_InProcessReplayClient(client, PROFILE_PATHS[name]),
        )
        ok = result.healthy and result.replay_ok
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name} healthy={result.healthy} "
            f"replay_ok={result.replay_ok} failure_rate={result.failure_rate}"
        )
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
