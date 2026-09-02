#!/usr/bin/env python3
"""Verify Helm chart structure and optional helm template render."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "deploy" / "helm" / "cfi-fed"

REQUIRED = [
    CHART / "Chart.yaml",
    CHART / "values.yaml",
    CHART / "templates" / "_helpers.tpl",
    CHART / "templates" / "namespace.yaml",
    CHART / "templates" / "configmap.yaml",
    CHART / "templates" / "secret.yaml",
    CHART / "templates" / "registry.yaml",
    CHART / "templates" / "coordinator.yaml",
    CHART / "templates" / "aggregator.yaml",
    CHART / "templates" / "ingress.yaml",
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
        print("Missing Helm chart files:", ", ".join(missing), file=sys.stderr)
        return 1

    chart_yaml = (CHART / "Chart.yaml").read_text(encoding="utf-8")
    if "name: cfi-fed" not in chart_yaml:
        print("Chart.yaml missing chart name", file=sys.stderr)
        return 1

    helm = shutil.which("helm")
    if helm:
        result = subprocess.run(
            [
                helm,
                "template",
                "cfi-fed",
                str(CHART),
                "--set",
                "registry.databaseUrl=postgresql://user:pass@postgres:5432/cfi",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout, file=sys.stderr)
            return result.returncode
        for needle in ("cfi-registry", "cfi-coordinator", "cfi-aggregator", "CFI_DATABASE_URL", "CFI_REGISTRY_URL"):
            if needle not in result.stdout:
                print(f"helm template output missing {needle}", file=sys.stderr)
                return 1
        print(f"Helm chart OK (helm template): {len(result.stdout.splitlines())} lines")
    else:
        print("Helm chart OK (static validation; helm CLI not installed)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
