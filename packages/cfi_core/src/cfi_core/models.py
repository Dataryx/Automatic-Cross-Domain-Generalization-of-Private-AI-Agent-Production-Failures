"""Core CFI types and enumerations (Definition 5, Table II)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class NodeType(str, Enum):
    OBSERVATION = "Observation"
    CONDITION = "Condition"
    RULE = "Rule"
    EXCEPTION = "Exception"
    AUTHORITY = "Authority"
    DECISION = "Decision"
    VERIFICATION = "Verification"
    ACTION = "Action"
    EXTERNAL_EFFECT = "ExternalEffect"
    OBLIGATION = "Obligation"
    OUTCOME = "Outcome"


class EdgeType(str, Enum):
    PRECEDES = "precedes"
    DEPENDS_ON = "depends_on"
    ENABLES = "enables"
    FORBIDS = "forbids"
    OVERRIDES = "overrides"
    REQUIRES = "requires"
    OBSERVED_AS = "observed_as"
    COMMITS = "commits"
    CAUSES = "causes"
    COMPENSATES = "compensates"
    VIOLATES = "violates"


# Namespaced extension edge (Appendix G resolution)
CORE_SUPPORTS = "core.ext/supports"


class DisclosureTier(str, Enum):
    PUBLIC = "public"
    MEMBER_ONLY = "member-only"
    RESTRICTED_BILATERAL = "restricted-bilateral"
    EMBARGOED = "embargoed"
    NON_SHAREABLE = "non-shareable"


class EdgeStatus(str, Enum):
    PRESENT = "present"
    REQUIRED_BUT_ABSENT = "required_but_absent"


class EventType(str, Enum):
    OBSERVATION = "observation"
    POLICY_LOOKUP = "policy_lookup"
    DECISION = "decision"
    TOOL_CALL = "tool_call"
    APPROVAL = "approval"
    ACTION = "action"
    STATE_MUTATION = "state_mutation"
    COMPENSATION = "compensation"
    TERMINATION = "termination"


class ProvenanceClass(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    ASSERTED = "asserted"


class ValueClass(str, Enum):
    ABOVE_THRESHOLD = "above_threshold"
    BELOW_THRESHOLD = "below_threshold"
    STALE_AFTER_UPDATE = "stale_after_update"
    EXCEPTION_ACTIVE = "exception_active"
    IRREVERSIBLE_EXTERNAL = "irreversible_external"


class TemporalConstraint(BaseModel):
    relation: Literal["before", "after", "within_duration", "no_action_until"]
    source_role: str
    target_role: str
    duration_ms: int | None = None
    status: EdgeStatus = EdgeStatus.PRESENT


class CardinalityConstraint(BaseModel):
    role: str
    node_type: NodeType
    multiplicity: Literal["required", "optional", "exactly_one", "at_least_one", "bounded"]
    bound: int | None = None


class OracleSpec(BaseModel):
    kind: Literal["state_predicate", "event_order", "authorization", "adjudicated_rubric"]
    expression: str
    evidence_requirements: list[str] = Field(default_factory=list)


class RiskMetadata(BaseModel):
    severity: float = Field(ge=0.0, le=1.0)
    reversibility: Literal["reversible", "partially_reversible", "irreversible"]
    affected_capability: str
    confidence: float = Field(ge=0.0, le=1.0)
    review_status: Literal["pending", "approved", "rejected"] = "pending"
    disclosure_tier: DisclosureTier = DisclosureTier.MEMBER_ONLY


class ReviewAttestation(BaseModel):
    reviewer_id: str
    role: str
    judgment: Literal["approve", "reject", "needs_revision"]
    timestamp: str
    notes: str = ""


class ProvenanceRecord(BaseModel):
    schema_version: str = "cfi/1.0"
    compiler_version: str
    evidence_digest: str  # local-only reference digest
    reviewer_attestations: list[ReviewAttestation] = Field(default_factory=list)
    supersession_chain: list[str] = Field(default_factory=list)
    process_attestation: str = ""


class ReleaseMetadata(BaseModel):
    tier: DisclosureTier
    source_domain: Literal["withheld"] = "withheld"
    free_text: bool = False
    exact_literals: bool = False
    expiration: str | None = None
    embargo_until: str | None = None


class CFINode(BaseModel):
    id: str
    type: NodeType
    role: str | None = None
    value_class: ValueClass | None = None
    risk: str | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("role")
    @classmethod
    def role_no_domain_nouns(cls, v: str | None) -> str | None:
        if v is None:
            return v
        prohibited = {"refund", "purchase", "patient", "customer", "invoice", "retail"}
        tokens = set(v.lower().replace("-", "_").split("_"))
        if tokens & prohibited:
            raise ValueError(f"Role '{v}' contains prohibited domain vocabulary")
        return v


class CFIEdge(BaseModel):
    source: str
    edge_type: str  # EdgeType or namespaced extension
    target: str
    status: EdgeStatus = EdgeStatus.PRESENT
    provenance: ProvenanceClass = ProvenanceClass.OBSERVED
    confidence: float | None = None
    explanation: str | None = None
    reviewer_id: str | None = None

    @model_validator(mode="after")
    def validate_provenance_metadata(self) -> CFIEdge:
        allowed = {e.value for e in EdgeType} | {CORE_SUPPORTS}
        if self.edge_type not in allowed:
            raise ValueError(f"Unknown edge type: {self.edge_type}")
        if self.provenance == ProvenanceClass.INFERRED:
            if self.confidence is None or not self.explanation:
                raise ValueError("Inferred edges require confidence and explanation")
        if self.provenance == ProvenanceClass.ASSERTED:
            if not self.reviewer_id:
                raise ValueError("Asserted edges require reviewer_id")
        return self


class CausalFailureInvariant(BaseModel):
    """Definition 5 — Causal Failure Invariant I = (G_I, C_I, Q_I, M_I, π_I, σ_I)."""

    schema: Literal["cfi/1.0"] = "cfi/1.0"
    id: str
    nodes: list[CFINode]
    edges: list[CFIEdge]
    temporal_constraints: list[TemporalConstraint] = Field(default_factory=list)
    cardinality_constraints: list[CardinalityConstraint] = Field(default_factory=list)
    failure_predicate: str
    controls: list[str] = Field(default_factory=list)
    oracle: OracleSpec
    risk: RiskMetadata
    release: ReleaseMetadata
    provenance: ProvenanceRecord
    signature: str | None = None
    certificate_chain: list[str] = Field(default_factory=list)

    @property
    def required_mapping_roles(self) -> list[str]:
        """Roles recipients must map; Outcome is derived (Appendix G #4)."""
        roles: list[str] = []
        for node in self.nodes:
            if node.type == NodeType.OUTCOME:
                continue
            if node.role:
                roles.append(node.role)
        return roles

    @model_validator(mode="after")
    def validate_graph(self) -> CausalFailureInvariant:
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                raise ValueError(f"Edge references unknown node: {edge.source}->{edge.target}")
        if self.release.free_text:
            raise ValueError("free_text must be false for released CFIs")
        if self.release.exact_literals:
            raise ValueError("exact_literals must be false by default")
        return self