"""Proposition 2 — fail-closed precision under random ontology ablation."""

import random

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext


def test_fail_closed_no_partial_emission() -> None:
    cfi = build_exception_precedence_cfi()
    roles = cfi.required_mapping_roles
    assert len(roles) == 6
    rng = random.Random(421337)
    for _ in range(100):
        available = set(roles)
        for role in roles:
            if rng.random() < 0.15:
                available.discard(role)
        mappings = [
            OntologyMapping(invariant_role=r, local_entity_id=f"l_{r}", status=MappingStatus.APPROVED)
            for r in available
        ]
        ctx = RecipientContext(domain="test", mappings=mappings)
        result = fail_closed_compile(cfi, ctx, manifest=None, seed=0)
        if len(available) < len(roles):
            assert result.abstained
        else:
            assert not result.abstained
            for case in result.cases:
                if not case.is_negative_control:
                    assert len(case.mapping) >= len(roles) - 1
