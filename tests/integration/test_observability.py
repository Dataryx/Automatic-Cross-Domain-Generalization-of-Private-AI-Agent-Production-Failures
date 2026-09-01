"""Service observability endpoint integration tests."""

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app
from services.aggregator.main import app as aggregator_app

ROOT = Path(__file__).resolve().parents[2]


def _signed_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("metrics-test")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_registry_metrics_reflect_state() -> None:
    client = TestClient(create_app(RegistryStore()))
    client.post("/cfi/register", json={"package": _signed_package()})
    metrics = client.get("/metrics").text
    assert "cfi_registry_registered_cfis 1.0" in metrics
    assert "cfi_registry_pending_reviews 1.0" in metrics


def test_aggregator_accountant_decrements_on_release() -> None:
    client = TestClient(aggregator_app)
    before = client.get("/accountant").json()["remaining_epsilon"]
    resp = client.post(
        "/aggregate",
        json={
            "contributions": [{"tenant_id": "t1", "failures": 1, "trials": 3, "coverage": 1.0}] * 5,
            "epsilon": 1.0,
            "minimum_k": 5,
            "measurement_spec_id": "obs-test",
            "cohort_id": "obs-test",
        },
    )
    assert resp.status_code == 200
    after = client.get("/accountant").json()["remaining_epsilon"]
    assert after < before


def test_verify_observability_script() -> None:
    script = ROOT / "scripts" / "verify_observability.py"
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
