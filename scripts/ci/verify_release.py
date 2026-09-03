#!/usr/bin/env python3
"""Verify signed release manifest and audit sink wiring."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tools/evaluation" / "output" / "release_manifest.json"


def verify_signed_release() -> tuple[bool, str]:
    if not MANIFEST.exists():
        return False, f"missing manifest: {MANIFEST}"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    from cfi_governance.release_attestation import verify_release_manifest

    if not verify_release_manifest(manifest):
        return False, "signature verification failed"
    dod = manifest.get("dod", {})
    if not dod.get("all_passed"):
        return False, f"DoD not all passed: {dod.get('passed')}/{dod.get('total')}"
    if manifest.get("pytest_exit_code", 1) != 0:
        return False, f"pytest exit code {manifest.get('pytest_exit_code')}"
    return True, "signed release manifest valid"


def verify_audit_sink() -> tuple[bool, str]:
    from fastapi.testclient import TestClient

    from cfi_contributor.packager import Packager
    from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
    from cfi_core.examples import build_exception_precedence_cfi
    from cfi_core.signing import KeyPair
    from cfi_governance.audit_sink import AuditSink
    from cfi_registry import RegistryStore, create_app

    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("verify-audit-sink")).package(cfi, verdict)
    assert pkg.cfi is not None

    with tempfile.TemporaryDirectory() as tmp:
        sink_path = Path(tmp) / "audit.ndjson"
        store = RegistryStore(audit_sink=AuditSink(file_path=sink_path))
        client = TestClient(create_app(store))
        client.post("/cfi/register", json={"package": pkg.cfi.model_dump(mode="json")})
        result = client.post("/audit/sink").json()
        if not result.get("flushed"):
            return False, f"audit sink flush failed: {result}"
        lines = sink_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return False, "audit sink file empty"
    return True, f"audit sink flushed {len(lines)} events"


def main() -> int:
    checks = [
        ("signed_release", verify_signed_release),
        ("audit_sink", verify_audit_sink),
    ]
    failed = False
    for name, fn in checks:
        ok, message = fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {message}")
        failed = failed or not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
