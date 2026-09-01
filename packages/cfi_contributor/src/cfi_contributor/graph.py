"""Incident graph builder — five relation classes with provenance metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, model_validator

from cfi_core.models import ProvenanceClass
from cfi_core.wire import TypedTrace


class RelationClass(str, Enum):
    CONTROL_FLOW = "control_flow"
    DATA_FLOW = "data_flow"
    POLICY_FLOW = "policy_flow"
    AUTHORITY_FLOW = "authority_flow"
    STATE_FLOW = "state_flow"


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: RelationClass
    provenance: ProvenanceClass
    confidence: float | None = None
    explanation: str | None = None
    reviewer_id: str | None = None
    source_ref: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> GraphEdge:
        if self.provenance == ProvenanceClass.INFERRED:
            if self.confidence is None or not self.explanation:
                raise ValueError("Inferred edges require confidence and explanation")
        if self.provenance == ProvenanceClass.ASSERTED:
            if not self.reviewer_id or not self.source_ref:
                raise ValueError("Asserted edges require reviewer_id and source_ref")
        return self


@dataclass
class IncidentGraph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)


class GraphBuilder:
    def build(self, trace: TypedTrace, policy_digest: str) -> IncidentGraph:
        graph = IncidentGraph()
        prev_id: str | None = None
        for event in trace.ordered_events():
            node_id = f"e{event.sequence_index}"
            graph.nodes[node_id] = {
                "event_type": event.event_type.value,
                "actor": event.actor,
                "digest": event.artifact_digest,
            }
            if prev_id:
                graph.edges.append(
                    GraphEdge(
                        source=prev_id,
                        target=node_id,
                        relation=RelationClass.CONTROL_FLOW,
                        provenance=ProvenanceClass.OBSERVED,
                    )
                )
            if event.event_type.value == "policy_lookup":
                graph.edges.append(
                    GraphEdge(
                        source=node_id,
                        target=f"policy:{policy_digest[:8]}",
                        relation=RelationClass.POLICY_FLOW,
                        provenance=ProvenanceClass.OBSERVED,
                    )
                )
            if event.event_type.value == "state_mutation":
                graph.edges.append(
                    GraphEdge(
                        source=node_id,
                        target="state_external",
                        relation=RelationClass.STATE_FLOW,
                        provenance=ProvenanceClass.OBSERVED,
                    )
                )
            prev_id = node_id
        return graph
