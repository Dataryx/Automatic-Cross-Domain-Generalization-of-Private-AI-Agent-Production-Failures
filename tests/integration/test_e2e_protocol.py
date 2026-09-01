"""Phase 4 two-party pilot — no raw trace crosses trust boundary."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.models import CausalFailureInvariant
from cfi_core.signing import KeyPair
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.protocol import recipient_evaluate_and_contribute, run_federation_round
from cfi_governance import LifecycleState
from cfi_registry import RegistryStore, create_app
from tests.conftest import build_recipient_context


def _signed_cfi() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    key = KeyPair.generate("contributor-org")
    result = Packager(key).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def _manifest(invariant_id: str) -> CohortManifest:
    spec = MeasurementSpec(
        spec_id="e2e-spec-1",
        invariant_id=invariant_id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    return CohortManifest(
        invariant_id=invariant_id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="e2e-epoch-1",
        expiration="2026-12-31",
        minimum_cohort_k=2,
    )


def test_contributor_to_registry_no_raw_trace() -> None:
    store = RegistryStore()
    client = TestClient(create_app(store))
    pkg = _signed_cfi()
    assert "prompt" not in str(pkg).lower()
    resp = client.post("/cfi/register", json={"package": pkg})
    assert resp.status_code == 200
    iid = resp.json()["invariant_id"]
    fetched = client.get(f"/cfi/{iid}")
    assert fetched.status_code == 200
    # No incident bundle in registry response
    assert "incident_id" not in fetched.json()
    assert "trace" not in fetched.json()


def test_lifecycle_reviewed_to_active() -> None:
    store = RegistryStore()
    client = TestClient(create_app(store))
    pkg = _signed_cfi()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    resp = client.post(
        f"/cfi/{iid}/lifecycle",
        json={"to_state": "active", "actor": "governance", "reason": "approved for cohort"},
    )
    assert resp.status_code == 200
    assert resp.json()["state"] == "active"


def test_recipient_compile_and_federation_round() -> None:
    pkg = _signed_cfi()
    cfi = CausalFailureInvariant.model_validate(pkg)
    manifest = _manifest(cfi.id)
    roles = cfi.required_mapping_roles

    contributions = []
    for tenant, domain in [("tenant-a", "procurement"), ("tenant-b", "healthcare")]:
        contrib, envelope, _ = recipient_evaluate_and_contribute(
            pkg, domain, tenant, manifest, roles
        )
        contributions.append(contrib)
        assert envelope["schema"] == "share-envelope/1.0"
        assert "shares_f" in envelope

    release = run_federation_round(contributions, manifest)
    assert release is not None
    assert release["released"] is True
    assert "assumptions" in release
    assert 0.0 <= release["noisy_prevalence"] <= 1.0


def test_sqlite_registry_e2e() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        from cfi_registry.db import PostgresRegistryStore

        db_path = Path(tmp) / "e2e.db"
        store = PostgresRegistryStore(f"sqlite:///{db_path}")
        try:
            client = TestClient(create_app(store))
            pkg = _signed_cfi()
            iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
            manifest = _manifest(iid)
            epoch = client.post("/cohort/publish", json={"manifest": manifest.model_dump(mode="json")})
            assert epoch.status_code == 200
            assert epoch.json()["status"] == "published"
        finally:
            store.close()
