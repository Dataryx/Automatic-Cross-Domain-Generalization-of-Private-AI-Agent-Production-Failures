#!/usr/bin/env python3
"""Verify multi-tenant corpus ingest and publish at scale (local bundles only)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1]
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
import pathsetup

ROOT = pathsetup.ROOT

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient
from corpus_tenants import materialize_tenant_corpus

SOURCE_BUNDLES = ROOT / "tools/evaluation" / "benchmarks" / "corpus" / "bundles"
TENANT_ROOT = ROOT / "tools/evaluation" / "benchmarks" / "corpus" / "tenants"
TENANT_COUNT = 5


def main() -> int:
    if TENANT_ROOT.exists() and any(TENANT_ROOT.rglob("*.json")):
        tenant_root = TENANT_ROOT
        expected_bundles = len(list(tenant_root.rglob("*.json")))
        tenant_label = f"prebuilt tenants ({expected_bundles} bundles)"
    else:
        tenant_label = f"{TENANT_COUNT} tenants"
        if not SOURCE_BUNDLES.exists():
            print(f"Missing source bundles: {SOURCE_BUNDLES}", file=sys.stderr)
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
        tmp_path = Path(tmp)
        if TENANT_ROOT.exists() and any(TENANT_ROOT.rglob("*.json")):
            tenant_root = TENANT_ROOT
        else:
            tenant_root = tmp_path / "tenants"
            materialize_tenant_corpus(SOURCE_BUNDLES, tenant_root, tenant_count=TENANT_COUNT)
            expected_bundles = TENANT_COUNT * len(list(SOURCE_BUNDLES.glob("*.json")))

        if not (TENANT_ROOT.exists() and any(TENANT_ROOT.rglob("*.json"))):
            pass  # expected_bundles set above
        else:
            expected_bundles = len(list(tenant_root.rglob("*.json")))

        ingest = CliRunner().invoke(
            contribute_app,
            [
                "ingest-corpus",
                "--input-dir",
                str(tenant_root),
                "--output-dir",
                str(tmp_path / "ingest"),
                "--extract",
                "--recursive",
            ],
        )
        if ingest.exit_code != 0:
            print(ingest.stdout, ingest.stderr, file=sys.stderr)
            client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
            return ingest.exit_code

        ingest_manifest = json.loads((tmp_path / "ingest" / "ingest_manifest.json").read_text(encoding="utf-8"))
        if ingest_manifest.get("validated", 0) != expected_bundles:
            print(
                f"Expected {expected_bundles} validated bundles, got {ingest_manifest.get('validated')}",
                file=sys.stderr,
            )
            client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
            return 1

        publish = CliRunner().invoke(
            contribute_app,
            [
                "ingest-publish",
                "--input-dir",
                str(tenant_root),
                "--output-dir",
                str(tmp_path / "publish"),
                "--registry-url",
                "http://test",
            ],
        )
        client_module.RegistryClient = original_client  # type: ignore[misc,assignment]
        if publish.exit_code != 0:
            print(publish.stdout, publish.stderr, file=sys.stderr)
            return publish.exit_code

        publish_manifest = json.loads((tmp_path / "publish" / "publish_manifest.json").read_text(encoding="utf-8"))
        registered = publish_manifest.get("registered", publish_manifest.get("registered_count", 0))
        if registered == 0:
            print("No CFIs registered from tenant corpus", file=sys.stderr)
            return 1

    print(
        f"Tenant corpus batch OK: {tenant_label} bundles={expected_bundles} "
        f"registered={registered} (structural collapse may dedupe CFIs)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
