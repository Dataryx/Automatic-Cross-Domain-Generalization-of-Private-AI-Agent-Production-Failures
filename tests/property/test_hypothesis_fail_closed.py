"""Hypothesis-backed fail-closed property tests."""

from hypothesis import given, settings
from hypothesis import strategies as st

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext


@settings(max_examples=50, deadline=None)
@given(st.data())
def test_fail_closed_abstains_on_missing_roles(data: st.DataObject) -> None:
    cfi = build_exception_precedence_cfi()
    roles = cfi.required_mapping_roles
    available = set(roles)
    for role in roles:
        if data.draw(st.booleans()):
            available.discard(role)
    mappings = [
        OntologyMapping(invariant_role=r, local_entity_id=f"l_{r}", status=MappingStatus.APPROVED)
        for r in available
    ]
    ctx = RecipientContext(domain="hypothesis", mappings=mappings)
    result = fail_closed_compile(cfi, ctx, manifest=None, seed=0)
    if len(available) < len(roles):
        assert result.abstained
    else:
        assert not result.abstained


def test_negative_control_ablation_reduces_case_count() -> None:
    cfi = build_exception_precedence_cfi()
    from cfi_recipient.ontology import build_recipient_context

    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    with_nc = fail_closed_compile(cfi, ctx, manifest=None, include_negative_controls=True)
    without_nc = fail_closed_compile(cfi, ctx, manifest=None, include_negative_controls=False)
    assert not with_nc.abstained and not without_nc.abstained
    assert len(with_nc.cases) > len(without_nc.cases)
    assert all(not c.is_negative_control for c in without_nc.cases)
