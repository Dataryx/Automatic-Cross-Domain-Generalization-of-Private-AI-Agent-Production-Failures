"""Prohibited CFI content variant tests (schema + lint)."""

import pytest

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGateVerdict
from cfi_core.canonicalize import Canonicalizer
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.schema_validate import validate_cfi
from cfi_core.signing import KeyPair


PROHIBITED_PREDICATES = [
    "api_key=sk-abcdefghijklmnopqrstuvwxyz123456",
    "password=secret123 AND action_committed",
    "exploit CVE-2024-1234 remote code execution",
    "wire $50000 on 2024-06-01 without approval",
]


def test_appendix_a_validates() -> None:
    cfi = build_exception_precedence_cfi()
    validate_cfi(cfi.model_dump(mode="json"))


@pytest.mark.parametrize("predicate", PROHIBITED_PREDICATES)
def test_prohibited_predicates_fail_lint_or_packager(predicate: str) -> None:
    cfi = build_exception_precedence_cfi()
    tainted = cfi.model_copy(update={"failure_predicate": predicate})
    violations = Canonicalizer.lint_for_release(tainted)
    verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.0)
    result = Packager(KeyPair.generate("test")).package(tainted, verdict)
    assert violations or not result.success
