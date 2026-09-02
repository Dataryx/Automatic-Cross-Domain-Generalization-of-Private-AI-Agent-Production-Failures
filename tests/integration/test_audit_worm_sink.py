"""WORM chain and idempotent audit sink integration tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_attestation import verify_audit_export
from cfi_governance.audit_idempotency import AuditIdempotencyLedger
from cfi_governance.audit_sink import AuditSink
from cfi_governance.audit_worm import read_worm_chain_head, worm_chain_hash
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("worm-sink")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_worm_chain_links_batches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CFI_AUDIT_SINK_SIGNED", "1")
    sink_path = tmp_path / "audit.ndjson"
    store = RegistryStore(audit_sink=AuditSink(file_path=sink_path, worm_chain=True))
    client = TestClient(create_app(store))
    client.post("/cfi/register", json={"package": _signed_package()})
    client.post("/audit/sink").json()
    record = json.loads(sink_path.read_text(encoding="utf-8").strip())
    assert "chain_hash" in record
    assert record["chain_prev"] == "0" * 64
    payload = record["payload"]
    assert verify_audit_export(payload)
    assert read_worm_chain_head(sink_path) == record["chain_hash"]


def test_idempotent_sink_skips_duplicate_batch(tmp_path: Path) -> None:
    sink_path = tmp_path / "audit.ndjson"
    ledger_path = tmp_path / "ledger.txt"
    sink = AuditSink(
        file_path=sink_path,
        worm_chain=True,
        idempotency=AuditIdempotencyLedger(persist_path=ledger_path),
    )
    events = [{"action": "register", "resource_id": "CFI-1"}]
    signed_batch = {
        "batch_id": "deadbeef" * 8,
        "events": events,
        "watermark_before": 0,
        "watermark_after": 1,
    }
    first = sink.emit(events, signed_batch=signed_batch)
    second = sink.emit(events, signed_batch=signed_batch)
    assert first.idempotent_skip is False
    assert first.file_appended == 1
    assert second.idempotent_skip is True
    assert second.file_appended == 0
    assert len(sink_path.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_worm_chain_hash_links_records() -> None:
    first = worm_chain_hash("0" * 64, '{"a":1}')
    second = worm_chain_hash(first, '{"b":2}')
    assert first != second
