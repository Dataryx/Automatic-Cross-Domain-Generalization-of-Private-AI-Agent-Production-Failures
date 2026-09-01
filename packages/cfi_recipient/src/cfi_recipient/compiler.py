"""Algorithm 3 — Fail-closed local compilation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from cfi_core.embedding import LocalScenarioGraph, preserves
from cfi_core.models import CausalFailureInvariant, NodeType
from cfi_core.signing import Verifier
from cfi_core.wire import CohortManifest
from cfi_recipient.ontology import MappingStatus, RecipientContext


@dataclass
class CompiledCase:
    case_id: str
    mapping: dict[str, str]
    initial_state: dict[str, Any]
    is_negative_control: bool = False
    broken_invariant: str | None = None


@dataclass
class CompilationResult:
    cases: list[CompiledCase] = field(default_factory=list)
    abstained: bool = False
    abstention_reason: str | None = None
    ambiguous_mappings: list[str] = field(default_factory=list)


def enumerate_typed_embeddings(
    invariant: CausalFailureInvariant,
    context: RecipientContext,
) -> list[dict[str, str]]:
    """Enumerate valid role-to-local-entity mappings."""
    required = set(invariant.required_mapping_roles)
    available = context.available_roles()
    if not required.issubset(available):
        return []
    embeddings: list[dict[str, str]] = []
    inv_nodes = {n.role: n.id for n in invariant.nodes if n.role and n.type != NodeType.OUTCOME}
    local_by_role = {
        m.invariant_role: m.local_entity_id
        for m in context.mappings
        if m.status == MappingStatus.APPROVED
    }
    if set(inv_nodes.keys()) <= set(local_by_role.keys()):
        mapping = {inv_nodes[role]: local_by_role[role] for role in inv_nodes}
        embeddings.append(mapping)
    return embeddings


def build_scenario_from_context(
    invariant: CausalFailureInvariant,
    context: RecipientContext,
    mapping: dict[str, str],
) -> LocalScenarioGraph:
    nodes: dict[str, dict[str, Any]] = {}
    for node in invariant.nodes:
        if node.type == NodeType.OUTCOME:
            continue
        local_id = mapping.get(node.id, node.id)
        nodes[local_id] = {"type": node.type.value, "role": node.role}
    edges: list[tuple[str, str, str]] = []
    for edge in invariant.edges:
        src = mapping.get(edge.source, edge.source)
        tgt = mapping.get(edge.target, edge.target)
        edges.append((src, edge.edge_type, tgt))
    reversibility = {
        mapping.get(n.id, n.id): "irreversible"
        for n in invariant.nodes
        if n.type == NodeType.ACTION
    }
    return LocalScenarioGraph(
        nodes=nodes,
        edges=edges,
        temporal=invariant.temporal_constraints,
        oracle_predicates={"main": invariant.oracle.expression},
        reversibility=reversibility,
    )


def static_validate(case: CompiledCase, invariant: CausalFailureInvariant, mapping: dict[str, str]) -> bool:
    return len(mapping) >= len(invariant.required_mapping_roles) - 1


def sandbox_ready(case: CompiledCase) -> bool:
    return bool(case.initial_state.get("sandbox_id"))


def fail_closed_compile(
    invariant: CausalFailureInvariant,
    context: RecipientContext,
    manifest: CohortManifest | None,
    case_budget: int = 1,
    seed: int = 0,
    include_negative_controls: bool = True,
) -> CompilationResult:
    """Algorithm 3."""
    if invariant.signature:
        verifier = Verifier()
        if not verifier.verify(invariant.model_dump(mode="json")):
            return CompilationResult(abstained=True, abstention_reason="invalid_signature")
    if manifest and manifest.frozen:
        if manifest.invariant_id != invariant.id:
            return CompilationResult(abstained=True, abstention_reason="manifest_mismatch")

    required = set(invariant.required_mapping_roles)
    available = context.available_roles()
    missing = required - available
    if missing:
        return CompilationResult(
            abstained=True,
            abstention_reason="missing_required_roles",
            ambiguous_mappings=list(missing),
        )

    embeddings = enumerate_typed_embeddings(invariant, context)
    valid: list[dict[str, str]] = []
    for mu in embeddings:
        scenario = build_scenario_from_context(invariant, context, mu)
        result = preserves(mu, invariant, scenario)
        if result.valid:
            valid.append(mu)

    if not valid:
        return CompilationResult(abstained=True, abstention_reason="no_valid_embedding")

    rng = random.Random(seed)
    cases: list[CompiledCase] = []
    for i, mu in enumerate(valid):
        for b in range(case_budget):
            case = CompiledCase(
                case_id=f"{invariant.id}-{context.domain}-{i}-{b}",
                mapping=mu,
                initial_state={"sandbox_id": f"sandbox-{rng.randint(0, 99999)}", "domain": context.domain},
            )
            if static_validate(case, invariant, mu) and sandbox_ready(case):
                cases.append(case)

    if not cases:
        return CompilationResult(abstained=True, abstention_reason="validation_failed")

    # Negative controls — break exactly one invariant at a time
    if include_negative_controls:
        for control in invariant.controls[:3]:
            nc = CompiledCase(
                case_id=f"nc-{control}",
                mapping=valid[0],
                initial_state={"sandbox_id": "sandbox-nc", "domain": context.domain},
                is_negative_control=True,
                broken_invariant=control,
            )
            cases.append(nc)

    return CompilationResult(cases=cases)
