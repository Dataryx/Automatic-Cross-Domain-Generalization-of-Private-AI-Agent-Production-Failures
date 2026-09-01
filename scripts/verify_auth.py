#!/usr/bin/env python3
"""Verify bearer-token auth when CFI_API_TOKEN is set."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app


def main() -> int:
    os.environ["CFI_API_TOKEN"] = "verify-auth-token"
    client = TestClient(create_app(RegistryStore()))
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("verify-auth")).package(cfi, verdict)
    if not pkg.success or pkg.cfi is None:
        print("packaging failed", file=sys.stderr)
        return 1

    denied = client.post("/cfi/register", json={"package": pkg.cfi.model_dump(mode="json")})
    if denied.status_code != 401:
        print(f"expected 401, got {denied.status_code}", file=sys.stderr)
        return 1

    allowed = client.post(
        "/cfi/register",
        json={"package": pkg.cfi.model_dump(mode="json")},
        headers={"Authorization": "Bearer verify-auth-token"},
    )
    if allowed.status_code != 200:
        print(f"expected 200, got {allowed.status_code}: {allowed.text}", file=sys.stderr)
        return 1

    print("Auth verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
