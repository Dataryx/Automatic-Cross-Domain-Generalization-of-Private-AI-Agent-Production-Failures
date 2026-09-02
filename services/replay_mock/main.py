"""Minimal mock replay server for HttpAgentReplayProvider integration tests."""

from __future__ import annotations

from services.replay_common import create_replay_app, run_replay_service

app = create_replay_app("replay_mock", "mock")

if __name__ == "__main__":
    run_replay_service(8010, "mock", "replay_mock")
