"""Cross-domain ontology fixtures for golden tests."""

from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext

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
