"""Recipient assess module tests."""

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.assess import assess_cfi


def test_assess_cfi_returns_metrics() -> None:
    result = assess_cfi(build_exception_precedence_cfi(), "procurement")
    assert len(result.compilation.cases) >= 1
    metrics = result.report.to_dict()
    assert "agent_susceptibility" in metrics
    assert "invariant_coverage" in metrics
