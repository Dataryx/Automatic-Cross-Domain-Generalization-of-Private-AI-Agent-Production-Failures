"""Registry human review API tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance import LifecycleState
from cfi_governance.review import ReviewStatus
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("review-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_register_enqueues_review() -> None:
    client = TestClient(create_app(RegistryStore()))
    pkg = _signed_package()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    queue = client.get("/review/queue").json()
    assert any(row["invariant_id"] == iid for row in queue)


def test_review_approval_activates_lifecycle() -> None:
    store = RegistryStore()
    client = TestClient(create_app(store))
    pkg = _signed_package()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    resp = client.post(
        f"/review/{iid}/decision",
        json={
            "status": ReviewStatus.APPROVED.value,
            "reviewer": "expert@org",
            "notes": "checklist complete",
            "checklist_complete": True,
        },
    )
    assert resp.status_code == 200
    lifecycle = client.get(f"/cfi/{iid}/lifecycle").json()
    assert lifecycle["state"] == LifecycleState.ACTIVE.value


def test_review_ui_returns_html() -> None:
    client = TestClient(create_app(RegistryStore()))
    resp = client.get("/review/ui")
    assert resp.status_code == 200
    assert "CFI Review Queue" in resp.text
    assert "release-gate checklist" in resp.text.lower()


def test_review_ticket_detail_includes_checklist() -> None:
    client = TestClient(create_app(RegistryStore()))
    pkg = _signed_package()
    iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
    detail = client.get(f"/review/{iid}").json()
    assert detail["invariant_id"] == iid
    assert len(detail["checklist"]) == 12
    ui = client.get(f"/review/{iid}/ui")
    assert ui.status_code == 200
    assert "Release gate checklist" in ui.text
