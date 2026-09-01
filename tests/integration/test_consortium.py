"""Consortium Phase 5 integration tests."""

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_core.examples import build_exception_precedence_cfi
from cfi_federation.consortium import (
    ConsortiumConfig,
    ConsortiumCoordinator,
    ParticipationStatus,
    TenantIdentity,
)
from tests.integration.test_e2e_protocol import _manifest, _signed_cfi


def test_adversaries_low_on_canonical_cfi() -> None:
    cfi = build_exception_precedence_cfi()
    report = ReleaseGateAdversaries().score_cfi(cfi)
    assert report.source_attribution < 0.3
    assert report.reconstruction < 0.3


def test_consortium_releases_with_12_tenants() -> None:
    pkg = _signed_cfi()
    manifest = _manifest(pkg["id"])
    roles = build_exception_precedence_cfi().required_mapping_roles
    identities = [
        TenantIdentity(tenant_id=f"t-{i}", org_family=f"org-{i % 6}", compiler_version="0.1.0")
        for i in range(12)
    ]
    config = ConsortiumConfig(minimum_k=10, dropout_rate=0.0)
    result = ConsortiumCoordinator(config).run_round(
        pkg, manifest, identities, roles,
        ["procurement", "healthcare", "data_operations"],
        seed=421337,
    )
    assert result.released
    assert result.participants >= 10
    assert result.noisy_prevalence is not None


def test_sybil_cap_rejects_excess_family() -> None:
    identities = [
        TenantIdentity(tenant_id=f"t-{i}", org_family="same-org", compiler_version="0.1.0")
        for i in range(5)
    ]
    subs = ConsortiumCoordinator().admit_tenants(identities)
    rejected = [s for s in subs if s.status == ParticipationStatus.REJECTED_SYBIL]
    assert len(rejected) >= 3


def test_below_minimum_k_blocks_release() -> None:
    pkg = _signed_cfi()
    manifest = _manifest(pkg["id"])
    roles = build_exception_precedence_cfi().required_mapping_roles
    identities = [
        TenantIdentity(tenant_id=f"t-{i}", org_family=f"org-{i}", compiler_version="0.1.0")
        for i in range(5)
    ]
    config = ConsortiumConfig(minimum_k=10, dropout_rate=0.0)
    result = ConsortiumCoordinator(config).run_round(
        pkg, manifest, identities, roles, ["procurement"], seed=1
    )
    assert not result.released
    assert result.reason == "below_minimum_k"
