#!/usr/bin/env python3
"""Cross-boundary smoke: contributor publish -> recipient fetch -> local compile."""

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
from cfi_core.models import CausalFailureInvariant
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import build_recipient_context
from cfi_registry import RegistryStore, create_app
from cfi_registry.client import RegistryClient


def main() -> int:
    app = create_app(RegistryStore())
    expected_id = build_exception_precedence_cfi().id

    def client_factory(base_url: str, token: str | None = None) -> RegistryClient:
        if base_url.rstrip("/") == "http://test":
            return RegistryClient.for_app(app)
        return RegistryClient(base_url, token=token)

    import cfi_registry.client as client_module

    original_client = client_module.RegistryClient
    client_module.RegistryClient = client_factory  # type: ignore[misc,assignment]

    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "published.json"
        fetched = Path(tmp) / "fetched.json"
        runner = CliRunner()
        publish = runner.invoke(
            contribute_app,
            ["publish", "--output", str(output), "--registry-url", "http://test"],
        )
        fetch = runner.invoke(
            recipient_app,
            [
                "fetch",
                "--invariant-id",
                expected_id,
                "--output",
                str(fetched),
                "--registry-url",
                "http://test",
            ],
        )
        client_module.RegistryClient = original_client  # type: ignore[misc,assignment]

        if publish.exit_code != 0 or fetch.exit_code != 0:
            print(publish.stdout, publish.stderr, fetch.stdout, fetch.stderr, file=sys.stderr)
            return 1

        package = json.loads(fetched.read_text(encoding="utf-8"))
        cfi = CausalFailureInvariant.model_validate(package)
        ctx = build_recipient_context("procurement", cfi.required_mapping_roles)
        compilation = fail_closed_compile(cfi, ctx, manifest=None)
        if compilation.abstained:
            print(f"Compile abstained: {compilation.abstention_reason}", file=sys.stderr)
            return 1

    print(f"Cross-boundary OK: published and compiled {expected_id} ({len(compilation.cases)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
