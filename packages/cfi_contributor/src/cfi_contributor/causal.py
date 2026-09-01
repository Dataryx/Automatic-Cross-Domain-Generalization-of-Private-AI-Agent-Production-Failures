"""Algorithm 1 — Counterfactual candidate scoring."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from cfi_contributor.graph import IncidentGraph


@dataclass
class InterventionResult:
    intervention: str
    failure_rate: float
    evidence: dict[str, float] = field(default_factory=dict)


@dataclass
class CausalCandidate:
    component: str
    delta: float
    baseline_rate: float
    intervention_results: list[InterventionResult]
    uncertainty: float
    evidence_summary: str


class DiagnosticProvider(ABC):
    @abstractmethod
    def propose_candidates(self, graph: IncidentGraph) -> list[str]:
        ...


class DefaultDiagnosticProvider(DiagnosticProvider):
    def propose_candidates(self, graph: IncidentGraph) -> list[str]:
        return list(graph.nodes.keys())


FailureOracle = Callable[[IncidentGraph], float]


def estimate_failure_rate(graph: IncidentGraph, oracle: FailureOracle, trials: int) -> float:
    if trials <= 0:
        return 0.0
    total = sum(oracle(graph) for _ in range(trials))
    return total / trials


def apply_intervention(graph: IncidentGraph, component: str, intervention: str) -> IncidentGraph:
    """Structural intervention do(z <- z')."""
    import copy

    g = copy.deepcopy(graph)
    if component in g.nodes:
        g.nodes[component]["intervention"] = intervention
    return g


def safe_replay(graph: IncidentGraph, oracle: FailureOracle, trials: int) -> float:
    return estimate_failure_rate(graph, oracle, trials)


def counterfactual_candidate_scoring(
    graph: IncidentGraph,
    oracle: FailureOracle,
    candidates: list[str],
    intervention_generator: Callable[[str], list[str]],
    trials: int,
) -> list[CausalCandidate]:
    """Algorithm 1 implementation."""
    baseline = estimate_failure_rate(graph, oracle, trials)
    results: list[CausalCandidate] = []
    for z in candidates:
        intervention_results: list[InterventionResult] = []
        rates: list[float] = []
        for j in intervention_generator(z):
            g_prime = apply_intervention(graph, z, j)
            rate = safe_replay(g_prime, oracle, trials)
            rates.append(rate)
            intervention_results.append(InterventionResult(intervention=j, failure_rate=rate))
        delta = baseline - min(rates) if rates else 0.0
        results.append(
            CausalCandidate(
                component=z,
                delta=delta,
                baseline_rate=baseline,
                intervention_results=intervention_results,
                uncertainty=1.0 / max(trials, 1),
                evidence_summary=(
                    "Counterfactual score is evidence for causal responsibility; "
                    "not a universal identification guarantee."
                ),
            )
        )
    return sorted(results, key=lambda c: (-c.delta, c.component))
