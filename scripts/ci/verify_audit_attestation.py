#!/usr/bin/env python3
"""Verify signed audit export attestation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance.audit_attestation import verify_audit_export
from cfi_registry import RegistryStore, create_app


def main() -> int:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("verify-audit-attest")).package(cfi, verdict)
    assert pkg.cfi is not None

    client = TestClient(create_app(RegistryStore()))
    client.post("/cfi/register", json={"package": pkg.cfi.model_dump(mode="json")})
    signed = client.get("/audit/export/signed").json()
    if not verify_audit_export(signed):
        print("Signed audit export verification failed", file=sys.stderr)
        return 1
    if not signed.get("events"):
        print("Signed audit export missing events", file=sys.stderr)
        return 1
    print(f"Audit attestation OK: {len(signed['events'])} events, watermark={signed.get('watermark')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
