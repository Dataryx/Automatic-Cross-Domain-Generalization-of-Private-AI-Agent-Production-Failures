#!/usr/bin/env python3
"""Verify cfi-contribute publish (extract + remote register) workflow."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def main() -> int:
    app = create_app(RegistryStore())

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_client = client_module.RegistryClient
    client_module.RegistryClient = client_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "published.json"
        runner = CliRunner()
        result = runner.invoke(
            contribute_app,
            [
                "publish",
                "--output",
                str(output),
                "--registry-url",
                "http://test",
            ],
        )
        client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
        if result.exit_code != 0:
            print(result.stdout, result.stderr, file=sys.stderr)
            return 1
        if not output.exists():
            print("publish did not write local output", file=sys.stderr)
            return 1
        package = json.loads(output.read_text(encoding="utf-8"))
        invariant_id = package["id"]
        if invariant_id not in result.stdout:
            print("publish output missing invariant id", file=sys.stderr)
            return 1

    print(f"Contribute publish OK: {invariant_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
