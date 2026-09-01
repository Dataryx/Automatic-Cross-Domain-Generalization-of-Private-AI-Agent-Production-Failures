#!/usr/bin/env python3
"""Smoke test: contributor extract via HttpAgentReplayProvider against replay mock."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.pipeline import ContributorPipeline
from cfi_contributor.replay import HttpAgentReplayProvider
from cfi_core.models import EventType
from cfi_core.signing import KeyPair
from cfi_core.wire import Incident, MinimizationConfig, TraceEvent, TypedTrace
from services.replay_mock.main import app as replay_app


class _InProcessReplayClient:
    """Route HttpAgentReplayProvider calls to an in-process replay mock."""

    def __init__(self, test_client: TestClient) -> None:
        self._client = test_client

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post("/replay", json=json)


def main() -> int:
    replay_client = TestClient(replay_app)
    replay = HttpAgentReplayProvider(
        "http://replay/replay",
        client=_InProcessReplayClient(replay_client),
    )
    incident = Incident(
        incident_id="live-replay-smoke",
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
        KeyPair.generate("live-replay-smoke"), replay=replay, seed=421337
    ).extract_from_incident(incident, raw, minimization, {i: True for i in range(1, 13)})
    if not report.package or not report.package.success or report.package.cfi is None:
        print(f"Extraction failed: {report.package}", file=sys.stderr)
        return 1
    print(f"Live replay smoke OK: {report.package.cfi.id}")
    if report.minimization and report.minimization.log:
        print(f"Minimization log entries: {len(report.minimization.log)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
