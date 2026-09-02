#!/usr/bin/env python3
"""Render Helm chart and validate with kubectl apply --dry-run=client."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "deploy" / "helm" / "cfi-fed"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _helm_cmd() -> list[str] | None:
    if shutil.which("helm"):
        return ["helm"]
    if shutil.which("docker"):
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{ROOT}:/work",
            "-w",
            "/work",
            "alpine/helm:3.14.0",
        ]
    return None


def render_chart() -> tuple[int, str, str]:
    helm = _helm_cmd()
    if helm is None:
        return 1, "", "helm CLI and docker unavailable"

    if helm[0] == "docker":
        from eval.compose_docker import docker_available

        if not docker_available(require=False):
            chart = subprocess.run(
                [sys.executable, "scripts/verify_helm_chart.py"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if chart.returncode != 0:
                return chart.returncode, "", chart.stderr or chart.stdout
            return 0, "", "SKIP: docker unavailable for helm template (static chart validation passed)"

    cmd = [
        *helm,
        "template",
        "cfi-fed",
        str(CHART),
        "--set",
        "registry.databaseUrl=postgresql://user:pass@postgres:5432/cfi",
        "--set",
        "ingress.enabled=true",
        "--set",
        "ingress.tls=true",
        "--set",
        "replayHooks.enabled=true",
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr or result.stdout


def kubectl_dry_run(manifest: str) -> tuple[int, str]:
    kubectl = shutil.which("kubectl")
    if kubectl is None:
        return 0, "SKIP: kubectl not installed"

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as handle:
        handle.write(manifest)
        path = handle.name

    result = subprocess.run(
        [kubectl, "apply", "--dry-run=client", "-f", path],
        capture_output=True,
        text=True,
    )
    Path(path).unlink(missing_ok=True)
    return result.returncode, result.stderr or result.stdout


def main() -> int:
    code, rendered, err = render_chart()
    if code != 0:
        print(err, file=sys.stderr)
        return code

    if not rendered.strip():
        print(err or "Helm deploy validation OK (static fallback)")
        return 0

    needles = (
        "cfi-replay-mock",
        "cfi-agentrx",
        "cfi-causalflow",
        "cfi-tau",
        "/agentrx",
        "/causalflow",
        "CFI_AGENTRX_URL",
    )
    for needle in needles:
        if needle not in rendered:
            print(f"helm template missing {needle}", file=sys.stderr)
            return 1

    k_code, k_out = kubectl_dry_run(rendered)
    if k_code != 0:
        print(k_out, file=sys.stderr)
        return k_code

    lines = len(rendered.splitlines())
    print(f"Helm deploy validation OK: {lines} rendered lines | {k_out.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
