"""API token authentication tests."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.auth import ApiTokenMiddleware, authorize_bearer
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app


def test_authorize_bearer_constant_time_match() -> None:
    assert authorize_bearer("Bearer secret-token", "secret-token")
    assert not authorize_bearer("Bearer wrong", "secret-token")
    assert not authorize_bearer(None, "secret-token")


def test_registry_blocks_register_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CFI_API_TOKEN", "registry-test-token")
    client = TestClient(create_app(RegistryStore()))
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("auth-test")).package(cfi, verdict)
    assert pkg.success and pkg.cfi is not None
    denied = client.post("/cfi/register", json={"package": pkg.cfi.model_dump(mode="json")})
    assert denied.status_code == 401
    allowed = client.post(
        "/cfi/register",
        json={"package": pkg.cfi.model_dump(mode="json")},
        headers={"Authorization": "Bearer registry-test-token"},
    )
    assert allowed.status_code == 200


def test_health_and_tracing_bypass_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CFI_API_TOKEN", "registry-test-token")
    client = TestClient(create_app(RegistryStore()))
    assert client.get("/health").status_code == 200
    assert client.get("/tracing").status_code == 200


def test_api_token_middleware_direct() -> None:
    app = FastAPI()

    @app.post("/secure")
    def secure() -> dict[str, str]:
        return {"ok": "1"}

    app.add_middleware(ApiTokenMiddleware, token="abc")
    client = TestClient(app)
    assert client.post("/secure").status_code == 401
    assert client.post("/secure", headers={"Authorization": "Bearer abc"}).status_code == 200
