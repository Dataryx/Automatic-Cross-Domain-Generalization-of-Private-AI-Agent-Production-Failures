#!/usr/bin/env python3
"""Verify contributor/recipient remote registry CLI against in-process registry."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def main() -> int:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    pkg = Packager(KeyPair.generate("verify-remote-cli")).package(cfi, verdict)
    if not pkg.success or pkg.cfi is None:
        print("Packaging failed", file=sys.stderr)
        return 1

    app = create_app(RegistryStore())
    package = pkg.cfi.model_dump(mode="json")
    invariant_id = package["id"]

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_client = client_module.RegistryClient
    client_module.RegistryClient = client_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        package_path = Path(tmp) / "package.json"
        package_path.write_text(json.dumps(package, indent=2), encoding="utf-8")
        out_path = Path(tmp) / "fetched.json"
        runner = CliRunner()
        reg = runner.invoke(
            contribute_app,
            ["register", "--package-path", str(package_path), "--registry-url", "http://test"],
        )
        status = runner.invoke(
            contribute_app,
            ["status", "--invariant-id", invariant_id, "--registry-url", "http://test"],
        )
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
        if reg.exit_code != 0 or status.exit_code != 0 or fetch.exit_code != 0:
            print(reg.stdout, reg.stderr, status.stdout, fetch.stdout, file=sys.stderr)
            return 1
        fetched = json.loads(out_path.read_text(encoding="utf-8"))
        if fetched.get("id") != invariant_id:
            print("Fetched CFI id mismatch", file=sys.stderr)
            client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
            return 1

    client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
    print(f"Remote registry CLI OK: {invariant_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
