"""Sandboxed AgentRx-style replay stub (diagnostic hook, not live production AgentRx)."""

from __future__ import annotations

from services.replay_common import create_replay_app, run_replay_service

app = create_replay_app("agentrx_stub", "agentrx")

if __name__ == "__main__":
    run_replay_service(8020, "agentrx", "agentrx_stub")
