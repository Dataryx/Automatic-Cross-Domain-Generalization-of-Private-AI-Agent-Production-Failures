"""Mitigation loop integration test."""

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.mitigation import MitigationCandidate, MitigationLayer, evaluate_mitigation
from cfi_recipient.sandbox import Sandbox
from tests.conftest import build_recipient_context


def _failing_agent(sb: Sandbox, trace) -> None:
    trace.state["review_complete"] = False
    sb.execute_tool(trace, "stub_po", {})


def _fixed_agent(sb: Sandbox, trace) -> None:
    trace.state["review_complete"] = True
    sb.execute_tool(trace, "stub_po", {})


def test_mitigation_lowers_susceptibility_and_passes_controls() -> None:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    mitigation = MitigationCandidate(
        layer=MitigationLayer.POLICY,
        description="enforce review before PO release",
        agent_fn=_fixed_agent,
    )
    report = evaluate_mitigation(compilation, cfi.oracle.expression, _failing_agent, mitigation)
    assert report.pre_susceptibility > report.post_susceptibility
    assert report.negative_controls_passed
    assert report.accepted
