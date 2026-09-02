#!/usr/bin/env python3
"""Verify CLI endpoint resolution from environment."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typer.testing import CliRunner

from cfi_cli import contribute_app
from cfi_contributor.service_urls import default_registry_url, resolve_service_url


def main() -> int:
    os.environ["CFI_REGISTRY_URL"] = "http://registry.example:9000"
    if default_registry_url() != "http://registry.example:9000":
        print("default_registry_url did not read CFI_REGISTRY_URL", file=sys.stderr)
        return 1

    runner = CliRunner()
    result = runner.invoke(contribute_app, ["endpoints"])
    if result.exit_code != 0:
        print(result.stdout, result.stderr, file=sys.stderr)
        return result.exit_code

    payload = json.loads(result.stdout)
    if payload.get("registry") != resolve_service_url("registry"):
        print(f"Unexpected endpoints payload: {payload}", file=sys.stderr)
        return 1

    print(f"CLI endpoints OK: registry={payload['registry']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
