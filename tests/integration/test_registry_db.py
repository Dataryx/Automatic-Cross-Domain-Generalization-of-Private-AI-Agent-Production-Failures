"""SQLite-backed registry persistence test."""

import tempfile
from pathlib import Path

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry.db import PostgresRegistryStore


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    key = KeyPair.generate("db-test")
    result = Packager(key).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_sqlite_registry_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "registry.db"
        store = PostgresRegistryStore(f"sqlite:///{db_path}")
        try:
            pkg = _signed_package()
            iid = store.register(pkg)
            fetched = store.get(iid)
            assert fetched["id"] == iid
        finally:
            store.close()
