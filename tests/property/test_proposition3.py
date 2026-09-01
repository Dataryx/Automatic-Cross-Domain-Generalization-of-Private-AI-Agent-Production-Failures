"""Proposition 3 — finite minimization terminates."""

from cfi_contributor.minimizer import typed_causal_core_minimization


def test_minimizer_terminates_and_is_minimal() -> None:
    candidate = {f"n{i}" for i in range(8)}

    def failure_preserving(s: set[str]) -> bool:
        return "n0" in s and "n1" in s

    def type_checker(s: set[str]) -> bool:
        return len(s) >= 2

    def privacy_cost(s: set[str]) -> float:
        return float(len(s))

    result = typed_causal_core_minimization(candidate, failure_preserving, type_checker, privacy_cost)
    core = result.core
    assert "n0" in core and "n1" in core
    # One-deletion minimal: removing any element breaks preservation or type
    for el in core:
        reduced = core - {el}
        assert not (type_checker(reduced) and failure_preserving(reduced))
    assert result.log, "Deletion log must be exposed for reviewers"
