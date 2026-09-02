#!/usr/bin/env python3
"""Verify live hook mode against running AgentRx/CausalFlow endpoints (compose or external)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.compose_docker import docker_available, require_docker_enabled, wait_for_url


def _ensure_hook_stubs() -> tuple[bool, bool]:
    """Start compose hook stubs when ports are not already serving /health."""
    import httpx

    agentrx_url = os.getenv("CFI_AGENTRX_URL", "http://127.0.0.1:8020")
    causalflow_url = os.getenv("CFI_CAUSALFLOW_URL", "http://127.0.0.1:8021")
    agentrx_base = agentrx_url.rsplit("/", 2)[0]
    causalflow_base = causalflow_url.rsplit("/", 2)[0]

    started_compose = False
    agentrx_ok = False
    causalflow_ok = False
    try:
        agentrx_ok = httpx.get(f"{agentrx_base}/health", timeout=3.0).status_code == 200
    except Exception:
        agentrx_ok = False
    try:
        causalflow_ok = httpx.get(f"{causalflow_base}/health", timeout=3.0).status_code == 200
    except Exception:
        causalflow_ok = False

    if agentrx_ok and causalflow_ok:
        return False, True

    if not require_docker_enabled():
        return False, agentrx_ok and causalflow_ok

    if not docker_available(require=True):
        return False, False

    compose_file = ROOT / "docker-compose.yml"
    up = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "up",
            "-d",
            "--build",
            "agentrx_stub",
            "causalflow_stub",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if up.returncode != 0:
        print(up.stderr or up.stdout, file=sys.stderr)
        return False, False
    started_compose = True

    ok_agentrx, _ = wait_for_url(f"{agentrx_base}/health", timeout_s=180.0)
    ok_causalflow, _ = wait_for_url(f"{causalflow_base}/health", timeout_s=180.0)
    return started_compose, ok_agentrx and ok_causalflow


def _probe_inprocess_live() -> int:
    """Fallback: exercise live-mode env checks with in-process stub apps."""
    import os

    from fastapi.testclient import TestClient

    from cfi_contributor.agent_hooks import PROFILE_PATHS, probe_replay_profile, require_live_hook_env
    from services.agentrx_stub.main import app as agentrx_app
    from services.causalflow_stub.main import app as causalflow_app

    class _InProcessReplayClient:
        def __init__(self, test_client: TestClient, path: str) -> None:
            self._client = test_client
            self._path = path

        def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
            return self._client.post(self._path, json=json)

    os.environ["CFI_HOOK_MODE"] = "live"
    os.environ["CFI_AGENTRX_URL"] = "http://127.0.0.1:8020/v1/replay"
    os.environ["CFI_CAUSALFLOW_URL"] = "http://127.0.0.1:8021/v1/counterfactual"
    require_live_hook_env()

    for name, app in (("agentrx", agentrx_app), ("causalflow", causalflow_app)):
        client = TestClient(app)
        result = probe_replay_profile(
            name,
            health_client=client,
            replay_client=_InProcessReplayClient(client, PROFILE_PATHS[name]),
        )
        if not (result.healthy and result.replay_ok):
            print(f"In-process live probe failed for {name}", file=sys.stderr)
            return 1

    print("Live hook mode OK (in-process fallback)")
    return 0


def main() -> int:
    started_compose, ready = _ensure_hook_stubs()
    if not ready:
        if not require_docker_enabled():
            print("SKIP: hook endpoints unavailable; using in-process live hook fallback")
            return _probe_inprocess_live()
        print("AgentRx/CausalFlow hook endpoints not reachable", file=sys.stderr)
        if started_compose:
            subprocess.run(
                ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "stop", "agentrx_stub", "causalflow_stub"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        return 1

    os.environ.setdefault("CFI_HOOK_MODE", "live")
    os.environ.setdefault("CFI_AGENTRX_URL", "http://127.0.0.1:8020/v1/replay")
    os.environ.setdefault("CFI_CAUSALFLOW_URL", "http://127.0.0.1:8021/v1/counterfactual")

    from typer.testing import CliRunner

    from cfi_cli import contribute_app

    result = CliRunner().invoke(
        contribute_app,
        ["probe-hooks", "--live", "--profile", "agentrx"],
    )
    if result.exit_code != 0:
        print(result.stdout, result.stderr, file=sys.stderr)
        if started_compose:
            subprocess.run(
                ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "stop", "agentrx_stub", "causalflow_stub"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        return result.exit_code

    result = CliRunner().invoke(
        contribute_app,
        ["probe-hooks", "--live", "--profile", "causalflow"],
    )
    if started_compose:
        subprocess.run(
            ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "stop", "agentrx_stub", "causalflow_stub"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    if result.exit_code != 0:
        print(result.stdout, result.stderr, file=sys.stderr)
        return result.exit_code

    print("Live hook mode OK (agentrx + causalflow)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
