"""Proposition 1 — structural compilation soundness under assumptions A1–A3."""

from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.embedding import preserves
from cfi_recipient.compiler import build_scenario_from_context, enumerate_typed_embeddings, fail_closed_compile
from tests.conftest import build_recipient_context


def test_emitted_cases_preserve_invariant_structure() -> None:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None, seed=0)
    assert not result.abstained
    for case in result.cases:
        if case.is_negative_control:
            continue
        scenario = build_scenario_from_context(cfi, ctx, case.mapping)
        check = preserves(case.mapping, cfi, scenario)
        assert check.valid, check.reasons


def test_proposition1_witnesses_structural_violation_not_missing_relation() -> None:
    """Oracle failure on positive case implies mapped invariant violation."""
    from cfi_recipient.sandbox import Sandbox, evaluate_case

    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None)
    positive = [c for c in result.cases if not c.is_negative_control][0]

    def bad_agent(sb: Sandbox, trace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    ev = evaluate_case(positive, cfi.oracle.expression, bad_agent)
    assert ev.verdict.value == "fail"
    embeddings = enumerate_typed_embeddings(cfi, ctx)
    assert embeddings, "Assumption A1: complete typed mapping exists"
