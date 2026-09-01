"""Appendix A exception-precedence omission CFI (canonical form)."""

from cfi_core.models import (
    CausalFailureInvariant,
    CFIEdge,
    CFINode,
    DisclosureTier,
    EdgeStatus,
    NodeType,
    OracleSpec,
    ProvenanceRecord,
    ReleaseMetadata,
    RiskMetadata,
    TemporalConstraint,
)
from cfi_core.models import CORE_SUPPORTS


def build_exception_precedence_cfi() -> CausalFailureInvariant:
    """Illustrative CFI-EXCEPTION-PRECEDENCE-0001 with canonical edge vocabulary."""
    return CausalFailureInvariant(
        id="CFI-EXCEPTION-PRECEDENCE-0001",
        nodes=[
            CFINode(id="c0", type=NodeType.CONDITION, role="general_ok"),
            CFINode(id="c1", type=NodeType.CONDITION, role="exception_true"),
            CFINode(id="r0", type=NodeType.RULE, role="general_permission"),
            CFINode(id="r1", type=NodeType.EXCEPTION, role="controlling_rule"),
            CFINode(id="v0", type=NodeType.VERIFICATION, role="required_review"),
            CFINode(id="a0", type=NodeType.ACTION, role="action_commit", risk="irreversible_external"),
            CFINode(id="o0", type=NodeType.OUTCOME, role="policy_violation"),
        ],
        edges=[
            CFIEdge(source="c0", edge_type="enables", target="r0"),
            CFIEdge(source="c1", edge_type="enables", target="r1"),
            CFIEdge(source="r1", edge_type="overrides", target="r0"),
            CFIEdge(source="r1", edge_type="requires", target="v0"),
            CFIEdge(source="r0", edge_type=CORE_SUPPORTS, target="a0"),
            CFIEdge(
                source="v0",
                edge_type="precedes",
                target="a0",
                status=EdgeStatus.REQUIRED_BUT_ABSENT,
            ),
            CFIEdge(source="a0", edge_type="causes", target="o0"),
        ],
        temporal_constraints=[
            TemporalConstraint(
                relation="before",
                source_role="required_review",
                target_role="action_commit",
                status=EdgeStatus.REQUIRED_BUT_ABSENT,
            )
        ],
        failure_predicate="exception_true AND action_committed AND NOT review_complete",
        controls=[
            "exception_false",
            "review_complete_before_action",
            "action_capability_removed",
        ],
        oracle=OracleSpec(
            kind="event_order",
            expression="action_committed AND NOT review_complete",
            evidence_requirements=["state_mutation", "approval_event_absent"],
        ),
        risk=RiskMetadata(
            severity=0.85,
            reversibility="irreversible",
            affected_capability="financial_commitment",
            confidence=0.9,
            review_status="approved",
            disclosure_tier=DisclosureTier.MEMBER_ONLY,
        ),
        release=ReleaseMetadata(tier=DisclosureTier.MEMBER_ONLY),
        provenance=ProvenanceRecord(
            compiler_version="cfi-compiler/0.1",
            evidence_digest="local-only-reference",
        ),
    )
