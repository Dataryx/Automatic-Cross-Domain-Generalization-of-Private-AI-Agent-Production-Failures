"""Local ontology and policy adapter — mappings never leave tenant."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel


class MappingStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActionSpec(BaseModel):
    role: str
    side_effect_class: str
    reversibility: str
    approval_threshold: str
    tool_endpoint: str
    sandbox_adapter: str


class RuleSpec(BaseModel):
    role: str
    condition: str
    authority: str
    priority: int
    exceptions: list[str] = []
    evidence_source: str = ""


class VerificationSpec(BaseModel):
    role: str
    actor_or_check: str
    required_timing: str
    completion_observable: str


class OntologyMapping(BaseModel):
    invariant_role: str
    local_entity_id: str
    status: MappingStatus = MappingStatus.PROPOSED
    proposer: str = ""
    approver: str | None = None


@dataclass
class RecipientContext:
    """D_j = (O_j, P_j, T_j, V_j, Σ^sandbox_j)."""

    domain: str
    actions: dict[str, ActionSpec] = field(default_factory=dict)
    rules: dict[str, RuleSpec] = field(default_factory=dict)
    verifications: dict[str, VerificationSpec] = field(default_factory=dict)
    mappings: list[OntologyMapping] = field(default_factory=list)
    ontology_freshness: str = ""
    stale_warning: bool = False

    def available_roles(self) -> set[str]:
        approved = {m.invariant_role for m in self.mappings if m.status == MappingStatus.APPROVED}
        return approved

    def mark_stale_if_needed(self, max_age_days: int, age_days: int) -> None:
        self.stale_warning = age_days > max_age_days
