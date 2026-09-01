"""Wire and storage types: incident, trace, deployment, measurement spec."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from cfi_core.models import EventType


class UnknownValue(str, Enum):
    UNKNOWN = "unknown"


class TraceEvent(BaseModel):
    """Definition 2 — typed trace event."""

    event_type: EventType
    actor: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    state_before: str | Literal["unknown"] = "unknown"
    state_after: str | Literal["unknown"] = "unknown"
    provenance_label: str = ""
    artifact_digest: str = ""
    concurrent_with: list[int] = Field(default_factory=list)  # event indices
    sequence_index: int = 0


class TypedTrace(BaseModel):
    events: list[TraceEvent]

    def ordered_events(self) -> list[TraceEvent]:
        return sorted(self.events, key=lambda e: e.sequence_index)


class Incident(BaseModel):
    """Definition 3 — production incident (local only)."""

    incident_id: str
    initiating_request_digest: str
    trace: TypedTrace
    policy_digest: str
    initial_state_digest: str
    terminal_state_digest: str
    expected_outcome: str
    observed_outcome: str
    severity: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_store_ref: str  # immutable local evidence pointer


class AgentDeployment(BaseModel):
    """Definition 1 — A = (M, H, T, P, O, V, Σ)."""

    model_id: str
    harness_id: str
    tool_set_id: str
    policy_set_id: str
    ontology_id: str
    verifier_ids: list[str] = Field(default_factory=list)
    state_schema_id: str = ""


class MinimizationConfig(BaseModel):
    """η, δ, λ — required configuration with no defaults (Appendix G #6)."""

    eta: float = Field(description="Failure preservation threshold η")
    delta: float = Field(description="Slack δ for removal test")
    lambda_nodes: float
    lambda_edges: float
    lambda_literals: float
    lambda_replay: float


class MeasurementSpec(BaseModel):
    """Signed measurement specification — travels with every aggregate."""

    spec_id: str
    invariant_id: str
    simulated_user: str
    tool_behavior: str
    judge: str
    evidence_bar: str
    trial_count: int
    aggregation_rule: str
    compiler_version: str
    assumptions: list[str] = Field(
        default_factory=lambda: [
            "Causal extraction from production traces is not guaranteed.",
            "DP protects tenant influence on aggregate, not poorly generalized CFIs.",
        ]
    )
    signature: str | None = None


class CohortManifest(BaseModel):
    invariant_id: str
    eligible_compiler_versions: list[str]
    measurement_spec: MeasurementSpec
    trial_count: int
    clipping_f: int
    clipping_n: int
    privacy_budget_epsilon: float
    aggregation_epoch: str
    expiration: str
    minimum_cohort_k: int = 10
    signature: str | None = None
    frozen: bool = False  # cannot amend after epoch opens
