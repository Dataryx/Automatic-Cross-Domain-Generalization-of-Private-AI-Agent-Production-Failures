"""Sandboxed CausalFlow-style counterfactual replay stub (not live production CausalFlow)."""

from __future__ import annotations

from services.replay_common import create_replay_app, run_replay_service

app = create_replay_app("causalflow_stub", "causalflow")

if __name__ == "__main__":
    run_replay_service(8021, "causalflow", "causalflow_stub")
