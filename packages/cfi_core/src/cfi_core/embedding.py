"""Constraint-preserving embedding checker — Definition 8, Preserves(μ, C_I, Q_I)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cfi_core.models import (
    CausalFailureInvariant,
    CardinalityConstraint,
    EdgeStatus,
    NodeType,
    TemporalConstraint,
)


@dataclass
class PreservesResult:
    valid: bool
    reasons: list[str] = field(default_factory=list)

    def fail(self, reason: str) -> PreservesResult:
        return PreservesResult(valid=False, reasons=self.reasons + [reason])


@dataclass
class LocalScenarioGraph:
    """Recipient-local typed scenario graph G_t."""

    nodes: dict[str, dict[str, Any]]
    edges: list[tuple[str, str, str]]  # source, edge_type, target
    temporal: list[TemporalConstraint] = field(default_factory=list)
    cardinalities: list[CardinalityConstraint] = field(default_factory=list)
    oracle_predicates: dict[str, str] = field(default_factory=dict)
    reversibility: dict[str, str] = field(default_factory=dict)


def preserves(
    mapping: dict[str, str],
    invariant: CausalFailureInvariant,
    scenario: LocalScenarioGraph,
) -> PreservesResult:
    """Deterministic checker over all seven embedding properties."""
    result = PreservesResult(valid=True)

    inv_nodes = {n.id: n for n in invariant.nodes}
    outcome_ids = {n.id for n in invariant.nodes if n.type == NodeType.OUTCOME}
    # 1. Node types
    for inv_id, local_id in mapping.items():
        if inv_id not in inv_nodes:
            return result.fail(f"unknown_invariant_node:{inv_id}")
        if local_id not in scenario.nodes:
            return result.fail(f"unknown_local_node:{local_id}")
        inv_node = inv_nodes[inv_id]
        inv_type = inv_node.type.value
        local_type = scenario.nodes[local_id].get("type")
        if inv_type != local_type:
            return result.fail(f"type_mismatch:{inv_id}->{local_id}")

    # 2. Required edges
    for edge in invariant.edges:
        if edge.source in outcome_ids or edge.target in outcome_ids:
            continue
        src = mapping.get(edge.source)
        tgt = mapping.get(edge.target)
        if src is None or tgt is None:
            if edge.status == EdgeStatus.REQUIRED_BUT_ABSENT:
                continue
            return result.fail(f"unmapped_edge_endpoint:{edge.source}->{edge.target}")
        if not _has_edge(scenario, src, edge.edge_type, tgt):
            if edge.status == EdgeStatus.REQUIRED_BUT_ABSENT:
                continue
            return result.fail(f"missing_edge:{edge.edge_type}:{src}->{tgt}")

    # 3. Cardinalities
    for cc in invariant.cardinality_constraints + scenario.cardinalities:
        count = sum(
            1
            for nid, node in scenario.nodes.items()
            if node.get("role") == cc.role and node.get("type") == cc.node_type.value
        )
        if cc.multiplicity == "required" and count < 1:
            return result.fail(f"cardinality_required:{cc.role}")
        if cc.multiplicity == "exactly_one" and count != 1:
            return result.fail(f"cardinality_exactly_one:{cc.role}:{count}")

    # 4. Temporal relations
    scenario_roles = {str(n.get("role")) for n in scenario.nodes.values() if n.get("role")}
    for tc in invariant.temporal_constraints + scenario.temporal:
        if tc.source_role not in scenario_roles:
            return result.fail(f"temporal_source_missing:{tc.source_role}")
        if tc.target_role not in scenario_roles:
            return result.fail(f"temporal_target_missing:{tc.target_role}")

    # 5. Policy precedence — overrides edges preserved
    override_edges = [e for e in invariant.edges if e.edge_type == "overrides"]
    for e in override_edges:
        src, tgt = mapping.get(e.source), mapping.get(e.target)
        if src and tgt and not _has_edge(scenario, src, "overrides", tgt):
            return result.fail(f"precedence_not_preserved:{src}->{tgt}")

    # 6. Action reversibility class
    for inv_id, local_id in mapping.items():
        inv_node = inv_nodes[inv_id]
        inv_risk = inv_node.risk
        if inv_risk and local_id in scenario.reversibility:
            if scenario.reversibility[local_id] not in ("reversible", "partially_reversible", "irreversible"):
                return result.fail(f"invalid_reversibility:{local_id}")

    # 7. Oracle predicates
    for pred_name, pred_expr in scenario.oracle_predicates.items():
        if not pred_expr:
            return result.fail(f"empty_oracle_predicate:{pred_name}")

    return result


def _has_edge(scenario: LocalScenarioGraph, src: str, edge_type: str, tgt: str) -> bool:
    return (src, edge_type, tgt) in scenario.edges
