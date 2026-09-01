"""Callable agent replay provider tests."""

from cfi_contributor.graph import IncidentGraph
from cfi_contributor.replay import CallableAgentReplayProvider


def test_callable_replay_provider() -> None:
    graph = IncidentGraph(nodes={"e0": {"event": "action"}}, edges=[])

    def agent_fn(g, seed: int) -> float:
        return 1.0 if "intervention" not in str(g.nodes) else 0.0

    provider = CallableAgentReplayProvider(agent_fn)
    ev = provider.estimate_failure_rate(graph, trials=3, seed=42)
    assert ev.failure_rate == 1.0
    replay = provider.replay_intervention(graph, "e0", "insert_verification", trials=2, seed=0)
    assert 0.0 <= replay.failure_rate <= 1.0
