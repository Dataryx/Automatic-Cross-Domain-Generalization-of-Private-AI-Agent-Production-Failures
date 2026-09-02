#!/usr/bin/env python3
"""Smoke test: contributor extract via HttpAgentReplayProvider across replay profiles."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.pipeline import ContributorPipeline
from cfi_contributor.replay import HttpAgentReplayProvider
from cfi_contributor.replay_profiles import REPLAY_PROFILES, resolve_replay_provider
from cfi_core.models import EventType
from cfi_core.signing import KeyPair
from cfi_core.wire import Incident, MinimizationConfig, TraceEvent, TypedTrace
from services.agentrx_stub.main import app as agentrx_app
from services.causalflow_stub.main import app as causalflow_app
from services.replay_mock.main import app as replay_mock_app


class _InProcessReplayClient:
    """Route HttpAgentReplayProvider calls to an in-process replay service."""

    def __init__(self, test_client: TestClient, path: str) -> None:
        self._client = test_client
        self._path = path

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post(self._path, json=json)


PROFILE_APPS: dict[str, tuple[object, str]] = {
    "mock": (replay_mock_app, "/replay"),
    "agentrx": (agentrx_app, "/v1/replay"),
    "causalflow": (causalflow_app, "/v1/counterfactual"),
}


def _run_profile(profile: str) -> tuple[bool, str]:
    app, path = PROFILE_APPS[profile]
    client = TestClient(app)
    replay = HttpAgentReplayProvider(
        REPLAY_PROFILES[profile].default_url,
        client=_InProcessReplayClient(client, path),
    )
    incident = Incident(
        incident_id=f"live-replay-{profile}",
        initiating_request_digest="digest-init",
        trace=TypedTrace(events=[TraceEvent(event_type=EventType.POLICY_LOOKUP, actor="agent")]),
        policy_digest="policy-digest",
        initial_state_digest="s0",
        terminal_state_digest="s1",
        expected_outcome="deny",
        observed_outcome="allow",
        severity=0.7,
        evidence_store_ref="local://evidence/smoke",
    )
    raw = {"events": [{"type": "policy_lookup", "actor": "agent", "index": 0}]}
    minimization = MinimizationConfig(
        eta=0.9, delta=0.05, lambda_nodes=1.0, lambda_edges=1.0, lambda_literals=1.0, lambda_replay=1.0
    )
    report = ContributorPipeline(
        KeyPair.generate(f"live-replay-{profile}"), replay=replay, seed=421337
    ).extract_from_incident(incident, raw, minimization, {i: True for i in range(1, 13)})
    if not report.package or not report.package.success or report.package.cfi is None:
        return False, f"{profile}: extraction failed"
    resolved = resolve_replay_provider(replay_profile=profile)
    if resolved._endpoint != REPLAY_PROFILES[profile].default_url:
        return False, f"{profile}: profile resolution mismatch"
    return True, f"{profile}: {report.package.cfi.id}"


def main() -> int:
    failed = False
    for profile in PROFILE_APPS:
        ok, message = _run_profile(profile)
        print(f"{'OK' if ok else 'FAIL'}: {message}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
