#!/usr/bin/env python3
"""Deploy CFI-Fed Helm chart to a local kind cluster (requires Docker + kind)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "deploy" / "helm" / "cfi-fed"
CLUSTER = "cfi-fed-local"
NAMESPACE = "cfi-fed"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def _docker_ok() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def _ensure_kind() -> bool:
    if shutil.which("kind"):
        return True
    print("SKIP: kind not installed (https://kind.sigs.k8s.io/)", file=sys.stderr)
    return False


def _ensure_cluster() -> None:
    clusters = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
    if CLUSTER in (clusters.stdout or ""):
        return
    _run(["kind", "create", "cluster", "--name", CLUSTER])
    _run(["kubectl", "cluster-info", "--context", f"kind-{CLUSTER}"])


def _helm_render() -> str:
    if shutil.which("helm"):
        helm = ["helm"]
    elif _docker_ok():
        helm = ["docker", "run", "--rm", "-v", f"{ROOT.resolve()}:/work", "-w", "/work", "alpine/helm:3.14.0"]
    else:
        print("helm or docker required", file=sys.stderr)
        raise SystemExit(1)

    result = _run(
        [
            *helm,
            "template",
            "cfi-fed",
            str(CHART),
            "--namespace",
            NAMESPACE,
            "--set",
            "registry.databaseUrl=postgresql://cfi:cfi@cfi-postgres:5432/cfi",
            "--set",
            "localDev.postgres.enabled=true",
            "--set",
            "ingress.enabled=false",
            "--set",
            "replayHooks.enabled=true",
            "--set",
            "image.pullPolicy=Never",
        ],
        check=True,
    )
    return result.stdout


def _load_image() -> None:
    if not _docker_ok():
        return
    build = _run(["docker", "build", "-t", "cfi-fed:latest", "."], check=False)
    if build.returncode != 0:
        print("Image build skipped (Dockerfile build failed)", file=sys.stderr)
        return
    _run(["kind", "load", "docker-image", "cfi-fed:latest", "--name", CLUSTER])


def main() -> int:
    if not _docker_ok():
        print("SKIP: Docker daemon not running", file=sys.stderr)
        return 0
    if not _ensure_kind():
        return 0
    _ensure_cluster()
    _load_image()

    manifest = _helm_render()
    manifest_path = ROOT / "tools/evaluation" / "output" / "helm_local_render.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest, encoding="utf-8")

    _run(["kubectl", "create", "namespace", NAMESPACE, "--dry-run=client", "-o", "yaml"], check=False)
    _run(["kubectl", "apply", "--context", f"kind-{CLUSTER}", "-f", str(manifest_path)])

    deadline = time.time() + 180
    while time.time() < deadline:
        pods = subprocess.run(
            ["kubectl", "get", "pods", "-n", NAMESPACE, "--context", f"kind-{CLUSTER}", "-o", "jsonpath={.items[*].status.phase}"],
            capture_output=True,
            text=True,
        )
        phases = (pods.stdout or "").split()
        if phases and all(p == "Running" for p in phases):
            print(f"Helm local deploy OK: {len(phases)} pod(s) Running in {NAMESPACE}")
            print(f"Manifest: {manifest_path}")
            return 0
        time.sleep(5)

    print("Pods did not reach Running within timeout", file=sys.stderr)
    _run(["kubectl", "get", "pods", "-n", NAMESPACE, "--context", f"kind-{CLUSTER}"], check=False)
    return 1


if __name__ == "__main__":
    sys.exit(main())
