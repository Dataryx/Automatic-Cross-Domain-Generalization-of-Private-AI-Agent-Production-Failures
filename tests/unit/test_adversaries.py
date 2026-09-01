"""Release-gate adversary unit tests."""

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_contributor.release_gate import GateOutcome, ReleaseGate
from cfi_core.examples import build_exception_precedence_cfi


def test_gate_auto_adversaries_approve_canonical() -> None:
    cfi = build_exception_precedence_cfi()
    verdict = ReleaseGate().run(cfi, {i: True for i in range(1, 13)})
    assert verdict.outcome in (GateOutcome.APPROVE, GateOutcome.RESTRICT_COHORT)


def test_adversaries_flag_domain_nouns() -> None:
    cfi = build_exception_precedence_cfi()
    report = ReleaseGateAdversaries().score_cfi(cfi, source_domain="retail")
    assert report.source_attribution >= 0.9
