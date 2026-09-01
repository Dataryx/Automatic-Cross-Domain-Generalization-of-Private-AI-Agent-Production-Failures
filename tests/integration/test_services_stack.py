"""Deployable services smoke tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation import ClippedContribution
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("svc-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_registry_service_register_and_fetch() -> None:
    client = TestClient(create_app(RegistryStore()))
    pkg = _signed_package()
    resp = client.post("/cfi/register", json={"package": pkg})
    assert resp.status_code == 200
    iid = resp.json()["invariant_id"]
    assert client.get(f"/cfi/{iid}").status_code == 200


def test_coordinator_freezes_epoch() -> None:
    from services.coordinator.main import app

    cfi = build_exception_precedence_cfi()
    spec = MeasurementSpec(
        spec_id="svc-spec",
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
        aggregation_epoch="svc-epoch-1",
        expiration="2026-12-31",
        minimum_cohort_k=2,
    )
    client = TestClient(app)
    resp = client.post("/epoch/open", json={"manifest": manifest.model_dump(mode="json")})
    assert resp.status_code == 200
    assert resp.json()["status"] == "frozen"


def test_aggregator_releases_with_k_contributions() -> None:
    from services.aggregator.main import app

    client = TestClient(app)
    contribs = [
        ClippedContribution(tenant_id=f"t{i}", failures=1, trials=3, coverage=1.0)
        for i in range(10)
    ]
    resp = client.post(
        "/aggregate",
        json={
            "contributions": [c.__dict__ for c in contribs],
            "epsilon": 1.0,
            "minimum_k": 10,
            "measurement_spec_id": "svc-spec",
            "cohort_id": "svc-cohort",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["released"] is True
    assert "noisy_prevalence" in body
