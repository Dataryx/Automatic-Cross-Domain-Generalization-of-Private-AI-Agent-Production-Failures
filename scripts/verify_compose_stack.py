#!/usr/bin/env python3
"""Docker Compose stack smoke test against live service health endpoints."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"

SERVICES = [
    ("registry", 8000, "/health"),
    ("coordinator", 8001, "/health"),
    ("aggregator", 8002, "/health"),
    ("replay_mock", 8010, "/health"),
    ("agentrx_stub", 8020, "/health"),
    ("causalflow_stub", 8021, "/health"),
]


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=True)


def _wait_for_health(name: str, port: int, path: str, timeout_s: float = 120.0) -> tuple[bool, str]:
    import httpx

    url = f"http://127.0.0.1:{port}{path}"
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                return True, f"{name} {url} OK"
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2.0)
    return False, f"{name} {url} failed: {last_error}"


def main() -> int:
    require_docker = os.getenv("CFI_REQUIRE_DOCKER", "0") == "1"
    if shutil.which("docker") is None:
        message = "Docker not available"
        if require_docker:
            print(message, file=sys.stderr)
            return 1
        print(f"SKIP: {message}")
        return 0
    daemon = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if daemon.returncode != 0:
        message = "Docker daemon not running"
        if require_docker:
            print(message, file=sys.stderr)
            if daemon.stderr:
                print(daemon.stderr, file=sys.stderr)
            return 1
        print(f"SKIP: {message}")
        return 0
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1

    print("Building and starting docker compose stack...")
    up = _run(["docker", "compose", "-f", str(COMPOSE), "up", "-d", "--build"], check=False)
    if up.returncode != 0:
        print(up.stderr or up.stdout, file=sys.stderr)
        return up.returncode

    failed: list[str] = []
    try:
        for name, port, path in SERVICES:
            ok, message = _wait_for_health(name, port, path)
            print(message)
            if not ok:
                failed.append(name)
        if failed:
            logs = _run(["docker", "compose", "-f", str(COMPOSE), "logs", "--tail", "80"], check=False)
            print(logs.stdout or logs.stderr, file=sys.stderr)
            print(f"Compose smoke failed: {', '.join(failed)}", file=sys.stderr)
            return 1
        print("Compose stack smoke OK")
        return 0
    finally:
        down = _run(["docker", "compose", "-f", str(COMPOSE), "down", "-v"], check=False)
        if down.returncode != 0:
            print(down.stderr or down.stdout, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
