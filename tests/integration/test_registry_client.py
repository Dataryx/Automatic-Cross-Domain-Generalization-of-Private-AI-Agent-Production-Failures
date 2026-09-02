"""Registry HTTP client tests."""

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def _package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("registry-client")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def test_registry_client_register_and_fetch() -> None:
    client = RegistryClient.for_app(create_app(RegistryStore()))
    package = _package()
    registered = client.register(package)
    invariant_id = registered["invariant_id"]
    fetched = client.get_cfi(invariant_id)
    lifecycle = client.get_lifecycle(invariant_id)
    assert fetched["id"] == invariant_id
    assert lifecycle["state"] == "reviewed"


def test_registry_client_audit_status() -> None:
    client = RegistryClient.for_app(create_app(RegistryStore()))
    client.register(_package())
    status = client.audit_status()
    assert status["event_count"] >= 1
