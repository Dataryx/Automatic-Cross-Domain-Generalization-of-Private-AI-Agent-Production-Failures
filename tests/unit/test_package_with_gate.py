"""Packager gate integration tests."""

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair


def test_package_with_gate_succeeds_on_canonical() -> None:
    cfi = build_exception_precedence_cfi()
    result = Packager(KeyPair.generate("gate-test")).package_with_gate(
        cfi, {i: True for i in range(1, 13)}
    )
    assert result.success
    assert result.cfi is not None
    assert result.cfi.signature


def test_package_with_gate_fails_on_leaky_domain() -> None:
    cfi = build_exception_precedence_cfi()
    result = Packager(KeyPair.generate("gate-test")).package_with_gate(
        cfi, {i: True for i in range(1, 13)}, source_domain="retail"
    )
    assert not result.success or result.cfi is None
