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


DOMAIN_MAPPINGS: dict[str, dict[str, str]] = {
    "procurement": {
        "general_ok": "spend_below_band",
        "exception_true": "new_vendor",
        "general_permission": "auto_release_band",
        "controlling_rule": "director_review_required",
        "required_review": "director_review",
        "action_commit": "release_purchase_order",
    },
    "healthcare": {
        "general_ok": "routine_eligibility",
        "exception_true": "experimental_use",
        "general_permission": "routine_coverage",
        "controlling_rule": "specialist_review_required",
        "required_review": "specialist_review",
        "action_commit": "authorize_procedure",
    },
    "data_operations": {
        "general_ok": "freshness_gate_passes",
        "exception_true": "schema_contract_break",
        "general_permission": "ordinary_freshness_gate",
        "controlling_rule": "manual_contract_approval",
        "required_review": "contract_approval",
        "action_commit": "publish_production_table",
    },
}


def build_recipient_context(domain: str, roles: list[str]) -> RecipientContext:
    mapping_spec = DOMAIN_MAPPINGS.get(domain, {})
    mappings = [
        OntologyMapping(
            invariant_role=role,
            local_entity_id=mapping_spec.get(role, f"local_{role}"),
            status=MappingStatus.APPROVED,
            approver="domain_expert",
        )
        for role in roles
    ]
    return RecipientContext(domain=domain, mappings=mappings)
