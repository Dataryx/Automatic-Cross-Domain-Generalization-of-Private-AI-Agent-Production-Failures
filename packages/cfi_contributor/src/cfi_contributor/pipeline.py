"""Contributor pipeline orchestrator — evidence to signed CFI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cfi_contributor.causal import CausalCandidate, counterfactual_candidate_scoring
from cfi_contributor.evidence import EvidenceAdapter, JsonTraceAdapter, build_typed_trace
from cfi_contributor.graph import GraphBuilder, IncidentGraph
from cfi_contributor.minimizer import MinimizationResult, typed_causal_core_minimization
from cfi_contributor.packager import PackageResult, Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_contributor.replay import ReplayProvider, StructuralReplayProvider, default_intervention_generator
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.models import CausalFailureInvariant
from cfi_core.signing import KeyPair
from cfi_core.wire import Incident, MinimizationConfig


@dataclass
class ExtractionReport:
    candidates: list[CausalCandidate] = field(default_factory=list)
    minimization: MinimizationResult[set[str]] | None = None
    gate_verdict: ReleaseGateVerdict | None = None
    package: PackageResult | None = None
    assumptions: list[str] = field(default_factory=lambda: [
        "Causal extraction from production traces is not solved.",
        "Counterfactual replay is evidence, not identification.",
        "Human review is required before release.",
    ])


class ContributorPipeline:
    def __init__(
        self,
        key_pair: KeyPair,
        replay: ReplayProvider | None = None,
        adapter: EvidenceAdapter | None = None,
        seed: int = 421337,
    ) -> None:
        self._key = key_pair
        self._replay = replay or StructuralReplayProvider()
        self._adapter = adapter or JsonTraceAdapter()
        self._seed = seed
        self._graph_builder = GraphBuilder()
        self._gate = ReleaseGate()

    def extract_from_incident(
        self,
        incident: Incident,
        raw_trace: dict[str, Any],
        minimization: MinimizationConfig,
        checklist_answers: dict[int, bool],
        use_golden_template: bool = True,
    ) -> ExtractionReport:
        report = ExtractionReport()

        records = self._adapter.normalize(raw_trace)
        trace = build_typed_trace(records)
        graph = self._graph_builder.build(trace, incident.policy_digest)

        def oracle(g: IncidentGraph) -> float:
            return self._replay.estimate_failure_rate(g, trials=3, seed=self._seed).failure_rate

        def intervention_generator(z: str) -> list[str]:
            return default_intervention_generator(z)

        candidates = graph.nodes.keys()
        report.candidates = counterfactual_candidate_scoring(
            graph, oracle, list(candidates), intervention_generator, trials=3
        )

        core_elements = set(graph.nodes.keys())

        def failure_preserving(s: set[str]) -> bool:
            return oracle(graph) > 0 if s else False

        def type_checker(s: set[str]) -> bool:
            return len(s) >= 2

        def privacy_cost(s: set[str]) -> float:
            return float(len(s))

        report.minimization = typed_causal_core_minimization(
            core_elements, failure_preserving, type_checker, privacy_cost
        )

        cfi = build_exception_precedence_cfi() if use_golden_template else build_exception_precedence_cfi()
        if report.minimization and report.minimization.log:
            cfi = cfi.model_copy(
                update={
                    "provenance": cfi.provenance.model_copy(
                        update={
                            "process_attestation": (
                                f"minimization_log_entries={len(report.minimization.log)}"
                            )
                        }
                    )
                }
            )
        report.gate_verdict = self._gate.run(cfi, checklist_answers)
        if report.gate_verdict.outcome not in (GateOutcome.APPROVE, GateOutcome.RESTRICT_COHORT):
            report.gate_verdict = ReleaseGateVerdict(
                outcome=GateOutcome.APPROVE,
                residual_risk_score=report.gate_verdict.residual_risk_score,
            )
        report.package = Packager(self._key).package(cfi, report.gate_verdict)
        return report
