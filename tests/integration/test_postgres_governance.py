"""Postgres-backed review and lifecycle persistence tests."""

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance import LifecycleState
from cfi_governance.review import ReviewStatus
from cfi_registry import create_app
from cfi_registry.db import PostgresRegistryStore


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("postgres-governance")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_postgres_review_and_lifecycle_survive_restart() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "governance.db"
        url = f"sqlite:///{db_path.as_posix()}"
        store = PostgresRegistryStore(url)
        client = TestClient(create_app(store))
        pkg = _signed_package()
        iid = client.post("/cfi/register", json={"package": pkg}).json()["invariant_id"]
        client.post(
            f"/review/{iid}/decision",
            json={
                "status": ReviewStatus.APPROVED.value,
                "reviewer": "expert@org",
                "notes": "approved after restart test",
                "checklist_complete": True,
            },
        )
        store.close()

        store2 = PostgresRegistryStore(url)
        client2 = TestClient(create_app(store2))
        lifecycle = client2.get(f"/cfi/{iid}/lifecycle").json()
        ticket = client2.get(f"/review/{iid}").json()
        queue = client2.get("/review/queue").json()
        store2.close()

        assert lifecycle["state"] == LifecycleState.ACTIVE.value
        assert ticket["status"] == ReviewStatus.APPROVED.value
        assert ticket["reviewer"] == "expert@org"
        assert not any(row["invariant_id"] == iid for row in queue)
