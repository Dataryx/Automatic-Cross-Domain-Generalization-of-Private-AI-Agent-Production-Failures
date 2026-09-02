"""Postgres-backed audit persistence tests."""

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import create_app
from cfi_registry.db import PostgresRegistryStore


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("postgres-audit")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_postgres_audit_events_persist_across_sessions() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "registry.db"
        url = f"sqlite:///{db_path.as_posix()}"
        store = PostgresRegistryStore(url)
        client = TestClient(create_app(store))
        pkg = _signed_package()
        iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
        store.close()

        store2 = PostgresRegistryStore(url)
        client2 = TestClient(create_app(store2))
        export = client2.get("/audit/export").json()
        store2.close()

        actions = [event["action"] for event in export["events"]]
        assert "cfi.registered" in actions
        assert any(event["resource_id"] == iid for event in export["events"])
