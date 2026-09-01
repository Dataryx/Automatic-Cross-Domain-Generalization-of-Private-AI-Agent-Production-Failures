"""Packager and signer — sole egress path from contributor tenant."""

from __future__ import annotations

from dataclasses import dataclass

from cfi_contributor.release_gate import GateOutcome, ReleaseGateVerdict
from cfi_core.canonicalize import Canonicalizer
from cfi_core.models import CausalFailureInvariant, DisclosureTier
from cfi_core.signing import KeyPair, Signer


@dataclass
class PackageResult:
    success: bool
    cfi: CausalFailureInvariant | None
    error: str | None = None


class Packager:
    """Can emit nothing but schema-valid, gate-approved, signed CFI."""

    def __init__(self, key_pair: KeyPair) -> None:
        self._signer = Signer(key_pair)
        self._canonicalizer = Canonicalizer()

    def package(
        self,
        cfi: CausalFailureInvariant,
        gate_verdict: ReleaseGateVerdict,
    ) -> PackageResult:
        if gate_verdict.outcome not in (GateOutcome.APPROVE, GateOutcome.RESTRICT_COHORT):
            return PackageResult(
                success=False,
                cfi=None,
                error=f"Gate outcome {gate_verdict.outcome} blocks release",
            )
        if cfi.release.tier == DisclosureTier.NON_SHAREABLE:
            return PackageResult(success=False, cfi=None, error="non_shareable tier")

        violations = Canonicalizer.lint_for_release(cfi)
        if violations:
            return PackageResult(success=False, cfi=None, error=f"Lint violations: {violations}")

        canonical, _report = self._canonicalizer.canonicalize(cfi)
        payload = canonical.model_dump(mode="json")
        sig, chain = self._signer.sign_package(payload)
        signed = canonical.model_copy(update={"signature": sig, "certificate_chain": chain})
        return PackageResult(success=True, cfi=signed)

    def attempt_smuggle(self, cfi: CausalFailureInvariant, smuggled_field: str) -> PackageResult:
        """Adversarial helper — always fails closed."""
        from cfi_contributor.release_gate import ReleaseGateVerdict

        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.0)
        tainted = cfi.model_copy(update={"failure_predicate": smuggled_field})
        return self.package(tainted, verdict)
