#!/usr/bin/env python3
"""End-to-end smoke: contributor publish -> recipient assess."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app, recipient_app
from cfi_core.examples import build_exception_precedence_cfi
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def main() -> int:
    app = create_app(RegistryStore())
    invariant_id = build_exception_precedence_cfi().id

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_client = client_module.RegistryClient
    client_module.RegistryClient = client_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "published.json"
        report_path = Path(tmp) / "assess.json"
        runner = CliRunner()
        publish = runner.invoke(
            contribute_app,
            ["publish", "--output", str(output), "--registry-url", "http://test"],
        )
        assess = runner.invoke(
            recipient_app,
            [
                "assess",
                "--invariant-id",
                invariant_id,
                "--registry-url",
                "http://test",
                "--domain",
                "procurement",
                "--output",
                str(report_path),
            ],
        )
        client_module.RegistryClient = original_client  # type: ignore[misc,assignment]

        if publish.exit_code != 0 or assess.exit_code != 0:
            print(publish.stdout, publish.stderr, assess.stdout, assess.stderr, file=sys.stderr)
            return 1

        report = json.loads(report_path.read_text(encoding="utf-8"))
        if "agent_susceptibility" not in report.get("metrics", {}):
            print("Assessment missing susceptibility metric", file=sys.stderr)
            return 1

    print(f"End-to-end workflow OK: {invariant_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
