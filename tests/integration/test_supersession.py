"""Registry supersession API."""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_governance import LifecycleState
from cfi_registry import RegistryStore, create_app


def _package(suffix: str = "") -> dict:
    cfi = build_exception_precedence_cfi()
    if suffix:
        cfi = cfi.model_copy(update={"id": f"{cfi.id}-{suffix}"})
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("supersede-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_supersession_marks_old_inactive() -> None:
    store = RegistryStore()
    client = TestClient(create_app(store))
    old_pkg = _package("v1")
    new_pkg = _package("v2")
    old_id = client.post("/cfi/register", json={"package": old_pkg}).json()["invariant_id"]
    new_id = client.post("/cfi/register", json={"package": new_pkg}).json()["invariant_id"]
    approve = client.post(
        f"/review/{old_id}/decision",
        json={"status": "approved", "reviewer": "governance@org", "notes": "promote"},
    )
    assert approve.status_code == 200
    resp = client.post(
        f"/cfi/{old_id}/supersede",
        json={"successor_id": new_id, "actor": "governance@org", "reason": "oracle tightened"},
    )
    assert resp.status_code == 200
    lifecycle = resp.json()
    assert lifecycle["state"] == LifecycleState.SUPERSEDED.value
    assert new_id in lifecycle["supersession_chain"]


def test_supersession_persisted_sqlite() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        from cfi_registry.db import PostgresRegistryStore

        db_path = Path(tmp) / "registry.db"
        store = PostgresRegistryStore(f"sqlite:///{db_path}")
        try:
            client = TestClient(create_app(store))
            old_id = client.post("/cfi/register", json={"package": _package("a")}).json()["invariant_id"]
            new_id = client.post("/cfi/register", json={"package": _package("b")}).json()["invariant_id"]
            client.post(
                f"/review/{old_id}/decision",
                json={"status": "approved", "reviewer": "governance@org"},
            )
            resp = client.post(
                f"/cfi/{old_id}/supersede",
                json={"successor_id": new_id, "actor": "governance@org"},
            )
            assert resp.status_code == 200
            assert resp.json()["state"] == LifecycleState.SUPERSEDED.value
        finally:
            store.close()
