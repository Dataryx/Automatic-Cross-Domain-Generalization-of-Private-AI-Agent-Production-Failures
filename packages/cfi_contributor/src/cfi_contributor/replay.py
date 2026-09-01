"""Pluggable safe replay for counterfactual analysis.

Causal extraction from production traces is NOT solved. Replay providers supply
evidence for Algorithm 1 but do not guarantee causal identification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from cfi_contributor.graph import IncidentGraph


@dataclass
class ReplayEvidence:
    failure_rate: float
    trials: int
    seeds: list[int] = field(default_factory=list)
    notes: str = ""


class ReplayProvider(ABC):
    @abstractmethod
    def estimate_failure_rate(self, graph: IncidentGraph, trials: int, seed: int) -> ReplayEvidence:
        ...

    @abstractmethod
    def replay_intervention(
        self,
        graph: IncidentGraph,
        component: str,
        intervention: str,
        trials: int,
        seed: int,
    ) -> ReplayEvidence:
        ...


class StructuralReplayProvider(ReplayProvider):
    """Deterministic structural replay when live agent is unavailable."""

    def estimate_failure_rate(self, graph: IncidentGraph, trials: int, seed: int) -> ReplayEvidence:
        # Failure if any node has intervention marker absent and graph has policy flow edges
        has_policy = any(e.relation.value == "policy_flow" for e in graph.edges)
        rate = 1.0 if has_policy else 0.0
        return ReplayEvidence(
            failure_rate=rate,
            trials=trials,
            seeds=[seed + i for i in range(trials)],
            notes="Structural replay only; not a live agent oracle.",
        )

    def replay_intervention(
        self,
        graph: IncidentGraph,
        component: str,
        intervention: str,
        trials: int,
        seed: int,
    ) -> ReplayEvidence:
        import copy

        g = copy.deepcopy(graph)
        if component in g.nodes:
            g.nodes[component]["intervention"] = intervention
        if intervention in ("enforce_precedence", "insert_verification"):
            rate = 0.0
        else:
            rate = self.estimate_failure_rate(g, trials, seed).failure_rate
        return ReplayEvidence(
            failure_rate=rate,
            trials=trials,
            seeds=[seed + i for i in range(trials)],
            notes=f"Intervention {intervention} on {component}",
        )


def default_intervention_generator(component: str) -> list[str]:
    return [
        "enforce_precedence",
        "insert_verification",
        "remove_unauthorized_capability",
        "noop",
    ]


class CallableAgentReplayProvider(ReplayProvider):
    """Live agent replay via injected callable — sandbox-only.

    The callable receives (graph, seed) and returns 1.0 for failure, 0.0 for pass.
    Integrate AgentRx/CausalFlow diagnostics behind this interface in production.
    """

    def __init__(self, agent_fn: object) -> None:
        self._agent_fn = agent_fn

    def estimate_failure_rate(self, graph: IncidentGraph, trials: int, seed: int) -> ReplayEvidence:
        rates: list[float] = []
        for i in range(trials):
            result = float(self._agent_fn(graph, seed + i))  # type: ignore[operator]
            rates.append(1.0 if result >= 0.5 else 0.0)
        return ReplayEvidence(
            failure_rate=sum(rates) / max(len(rates), 1),
            trials=trials,
            seeds=[seed + i for i in range(trials)],
            notes="Live agent replay via injected callable; causal identification not guaranteed.",
        )

    def replay_intervention(
        self,
        graph: IncidentGraph,
        component: str,
        intervention: str,
        trials: int,
        seed: int,
    ) -> ReplayEvidence:
        import copy

        g = copy.deepcopy(graph)
        if component in g.nodes:
            g.nodes[component]["intervention"] = intervention
        return self.estimate_failure_rate(g, trials, seed)


class HttpAgentReplayProvider(ReplayProvider):
    """POST incident graph to external replay service (AgentRx/CausalFlow hook).

    Expected JSON response: {"failure_rate": 0.0..1.0} or {"fail": true/false}.
    Sandbox-only; causal identification not guaranteed.
    """

    def __init__(self, endpoint: str, timeout: float = 30.0) -> None:
        self._endpoint = endpoint
        self._timeout = timeout

    def _call(self, graph: IncidentGraph, seed: int) -> float:
        import httpx

        payload = {
            "nodes": graph.nodes,
            "edges": [{"source": e.source, "target": e.target, "relation": e.relation.value} for e in graph.edges],
            "seed": seed,
        }
        resp = httpx.post(self._endpoint, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if "failure_rate" in data:
            return float(data["failure_rate"])
        if "fail" in data:
            return 1.0 if data["fail"] else 0.0
        raise ValueError("Replay endpoint must return failure_rate or fail")

    def estimate_failure_rate(self, graph: IncidentGraph, trials: int, seed: int) -> ReplayEvidence:
        rates = [self._call(graph, seed + i) for i in range(trials)]
        binary = [1.0 if r >= 0.5 else 0.0 for r in rates]
        return ReplayEvidence(
            failure_rate=sum(binary) / max(len(binary), 1),
            trials=trials,
            seeds=[seed + i for i in range(trials)],
            notes=f"HTTP replay to {self._endpoint}",
        )

    def replay_intervention(
        self,
        graph: IncidentGraph,
        component: str,
        intervention: str,
        trials: int,
        seed: int,
    ) -> ReplayEvidence:
        import copy

        g = copy.deepcopy(graph)
        if component in g.nodes:
            g.nodes[component]["intervention"] = intervention
        return self.estimate_failure_rate(g, trials, seed)
