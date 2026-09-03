#!/usr/bin/env python3
"""Verify corpus ingest -> publish workflow (bundles local, signed CFIs only egress)."""

from __future__ import annotations

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

BUNDLES = ROOT / "tools/evaluation" / "benchmarks" / "corpus" / "bundles"


def main() -> int:
    if not BUNDLES.exists():
        print(f"Missing bundles: {BUNDLES}", file=sys.stderr)
        return 1

    app = create_app(RegistryStore())

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_client = client_module.RegistryClient
    client_module.RegistryClient = client_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        result = CliRunner().invoke(
            contribute_app,
            [
                "ingest-publish",
                "--input-dir",
                str(BUNDLES),
                "--output-dir",
                tmp,
                "--registry-url",
                "http://test",
            ],
        )
        client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
        if result.exit_code != 0:
            print(result.stdout, result.stderr, file=sys.stderr)
            return 1
        publish_manifest = Path(tmp) / "publish_manifest.json"
        if not publish_manifest.exists():
            print("Missing publish_manifest.json", file=sys.stderr)
            return 1

    print("Corpus ingest-publish OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
