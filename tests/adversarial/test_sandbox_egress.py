"""Sandbox egress and kill-switch adversarial tests."""

from cfi_recipient.sandbox import OracleVerdict, Sandbox, SandboxTrace, evaluate_case
from cfi_recipient.compiler import CompiledCase


def _case() -> CompiledCase:
    return CompiledCase(
        case_id="adv-1",
        mapping={},
        initial_state={"sandbox_id": "sbx"},
    )


def test_egress_denied_blocks_tool() -> None:
    sb = Sandbox(egress_allowlist=["allowed_tool"])
    trace = SandboxTrace()
    action = sb.execute_tool(trace, "forbidden_api", {"x": 1})
    assert action.blocked
    assert action.reason == "egress_denied"
    assert "forbidden_api_committed" not in trace.state


def test_kill_switch_blocks_after_activation() -> None:
    sb = Sandbox(egress_allowlist=["stub_po"])
    trace = SandboxTrace()
    sb.kill()
    action = sb.execute_tool(trace, "stub_po", {})
    assert action.blocked
    assert action.reason == "kill_switch"


def test_evaluate_case_records_attempted_actions() -> None:
    def agent(sb: Sandbox, trace: SandboxTrace) -> None:
        sb.execute_tool(trace, "stub_po", {})

    result = evaluate_case(_case(), "expr", agent, sandbox=Sandbox(egress_allowlist=["stub_po"]))
    assert len(result.trace.attempted_actions) == 1
    assert result.verdict in (OracleVerdict.FAIL, OracleVerdict.PASS, OracleVerdict.UNKNOWN)
