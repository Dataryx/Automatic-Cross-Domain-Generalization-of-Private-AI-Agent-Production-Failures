"""Audit sink watermark deduplication tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_sink import AuditSink
from cfi_governance.audit_watermark import AuditWatermark
from cfi_registry import RegistryStore, create_app


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("watermark-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_audit_sink_watermark_skips_duplicate_exports(tmp_path: Path) -> None:
    sink_path = tmp_path / "audit.ndjson"
    watermark_path = tmp_path / "watermark.txt"
    store = RegistryStore(
        audit_sink=AuditSink(file_path=sink_path),
        watermark=AuditWatermark(persist_path=watermark_path),
    )
    client = TestClient(create_app(store))
    client.post("/cfi/register", json={"package": _signed_package()})

    first = client.post("/audit/sink").json()
    second = client.post("/audit/sink").json()

    assert first["exported_count"] == 1
    assert second["exported_count"] == 0
    assert second["watermark"] == first["watermark"]
    lines = sink_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["action"] == "cfi.registered"
    assert watermark_path.read_text(encoding="utf-8") == "1"


def test_watermark_persists_to_file(tmp_path: Path) -> None:
    path = tmp_path / "wm.txt"
    wm = AuditWatermark(persist_path=path)
    wm.advance(5)
    reloaded = AuditWatermark(persist_path=path)
    assert reloaded.value == 5
