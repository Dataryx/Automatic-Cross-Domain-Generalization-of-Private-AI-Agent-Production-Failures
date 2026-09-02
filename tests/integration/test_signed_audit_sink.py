"""Signed audit sink flush tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_attestation import verify_audit_export
from cfi_governance.audit_sink import AuditSink
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("signed-sink")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_signed_audit_sink_flush_writes_verifiable_batch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CFI_AUDIT_SINK_SIGNED", "1")
    sink_path = tmp_path / "audit.ndjson"
    store = RegistryStore(audit_sink=AuditSink(file_path=sink_path))
    client = TestClient(create_app(store))
    client.post("/cfi/register", json={"package": _signed_package()})
    result = client.post("/audit/sink").json()
    assert result["signed_batch"] is True
    line = json.loads(sink_path.read_text(encoding="utf-8").strip())
    assert verify_audit_export(line)
    assert line["watermark_after"] == 1
