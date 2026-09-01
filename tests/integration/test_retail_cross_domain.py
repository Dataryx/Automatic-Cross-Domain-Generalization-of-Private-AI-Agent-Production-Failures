"""Golden cross-domain integration test — Appendix B."""

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.sandbox import Sandbox, evaluate_case
from tests.conftest import build_recipient_context


def _failing_agent(sb: Sandbox, trace) -> None:
    trace.state["review_complete"] = False
    sb.execute_tool(trace, "stub_po", {"amount": 100})


def test_retail_invariant_compiles_all_targets() -> None:
    cfi = build_exception_precedence_cfi()
    for domain in ["procurement", "healthcare", "data_operations"]:
        ctx = build_recipient_context(domain, cfi.required_mapping_roles)
        result = fail_closed_compile(cfi, ctx, manifest=None, case_budget=1, seed=42)
        assert not result.abstained, f"{domain}: {result.abstention_reason}"
        positive = [c for c in result.cases if not c.is_negative_control]
        assert len(positive) >= 1


def test_positive_case_fails_and_negative_passes() -> None:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None, seed=42)
    positive = [c for c in result.cases if not c.is_negative_control][0]
    neg = [c for c in result.cases if c.is_negative_control][0]

    fail_eval = evaluate_case(positive, cfi.oracle.expression, _failing_agent)
    assert fail_eval.verdict.value == "fail"

    pass_eval = evaluate_case(neg, cfi.oracle.expression, _failing_agent)
    assert pass_eval.verdict.value == "pass"
