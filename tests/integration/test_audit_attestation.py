"""Signed audit export tests."""

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_attestation import sign_audit_export, verify_audit_export
from cfi_registry import RegistryStore, create_app


def test_signed_audit_export_verifies() -> None:
    payload = {"events": [{"action": "cfi.registered"}], "watermark": 0, "exported_at": "t"}
    signed = sign_audit_export(payload, KeyPair.generate("audit-test"))
    assert verify_audit_export(signed)


def test_registry_signed_audit_export_endpoint() -> None:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("audit-endpoint")).package(cfi, verdict)
    assert pkg.cfi is not None
    client = TestClient(create_app(RegistryStore()))
    client.post("/cfi/register", json={"package": pkg.cfi.model_dump(mode="json")})
    signed = client.get("/audit/export/signed").json()
    assert verify_audit_export(signed)
    assert signed["events"][0]["action"] == "cfi.registered"
