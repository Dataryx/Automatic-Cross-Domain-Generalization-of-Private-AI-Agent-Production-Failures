"""Registry audit export integration tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.review import ReviewStatus
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("audit-export")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_audit_export_records_register_and_review() -> None:
    client = TestClient(create_app(RegistryStore()))
    pkg = _signed_package()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    client.post(
        f"/review/{iid}/decision",
        json={"status": ReviewStatus.APPROVED.value, "reviewer": "auditor@org", "checklist_complete": True},
    )
    export = client.get("/audit/export").json()
    actions = [event["action"] for event in export["events"]]
    assert "cfi.registered" in actions
    assert "review.decision" in actions
    assert "lifecycle.transition" in actions
