"""Registry audit API tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("audit-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_audit_endpoint_returns_adversary_scores() -> None:
    client = TestClient(create_app(RegistryStore()))
    pkg = _signed_package()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    audit = client.get(f"/cfi/{iid}/audit")
    assert audit.status_code == 200
    body = audit.json()
    assert "adversary_scores" in body
    assert "source_attribution" in body["adversary_scores"]
