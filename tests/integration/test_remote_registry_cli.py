"""Remote registry CLI command tests."""

import json
from pathlib import Path

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def _write_package(path: Path) -> str:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("remote-cli")).package(cfi, verdict)
    assert result.success and result.cfi is not None
    path.write_text(json.dumps(result.cfi.model_dump(mode="json"), indent=2), encoding="utf-8")
    return result.cfi.id


def test_contribute_register_and_recipient_fetch_cli(tmp_path: Path, monkeypatch) -> None:
    app = create_app(RegistryStore())

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    monkeypatch.setattr("cfi_registry.client.RegistryClient", client_factory)
    package_path = tmp_path / "package.json"
    invariant_id = _write_package(package_path)
    runner = CliRunner()
    register = runner.invoke(
        contribute_app,
        ["register", "--package-path", str(package_path), "--registry-url", "http://test"],
    )
    assert register.exit_code == 0, register.stdout + register.stderr
    assert invariant_id in register.stdout

    status = runner.invoke(
        contribute_app,
        ["status", "--invariant-id", invariant_id, "--registry-url", "http://test"],
    )
    assert status.exit_code == 0
    assert "reviewed" in status.stdout

    out_path = tmp_path / "fetched.json"
    fetch = runner.invoke(
        recipient_app,
        [
            "fetch",
            "--invariant-id",
            invariant_id,
            "--output",
            str(out_path),
            "--registry-url",
            "http://test",
        ],
    )
    assert fetch.exit_code == 0, fetch.stdout + fetch.stderr
    fetched = json.loads(out_path.read_text(encoding="utf-8"))
    assert fetched["id"] == invariant_id
