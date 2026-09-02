"""Recipient federation contribution tests."""

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_recipient.federation_contrib import contribute_from_package


def _package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("fed-contrib")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_contribute_from_package_builds_envelope() -> None:
    pkg = _package()
    cfi = build_exception_precedence_cfi()
    spec = MeasurementSpec(
        spec_id="fed-test",
        invariant_id=cfi.id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    manifest = CohortManifest(
        invariant_id=cfi.id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="fed-test",
        expiration="2026-12-31",
        minimum_cohort_k=2,
    )
    result = contribute_from_package(
        pkg, domain="procurement", tenant_id="tenant-x", manifest=manifest, roles=cfi.required_mapping_roles
    )
    assert result.share_envelope["schema"] == "share-envelope/1.0"
    assert result.contribution.trials >= 1
