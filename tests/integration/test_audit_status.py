"""Registry audit status API tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_sink import AuditSink
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("audit-status")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_audit_status_reports_pending_export(tmp_path) -> None:
    sink_path = tmp_path / "audit.ndjson"
    store = RegistryStore(audit_sink=AuditSink(file_path=sink_path))
    client = TestClient(create_app(store))
    client.post("/cfi/register", json={"package": _signed_package()})

    status = client.get("/audit/status").json()
    assert status["event_count"] == 1
    assert status["pending_export"] == 1
    assert status["watermark"] == 0
    assert status["sink_configured"] is True

    client.post("/audit/sink")
    status_after = client.get("/audit/status").json()
    assert status_after["pending_export"] == 0
    assert status_after["watermark"] == 1
