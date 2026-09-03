#!/usr/bin/env python3
"""Docker Compose Postgres stack smoke test."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.postgres.yml"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=True)


def _wait_for_health(port: int, path: str, timeout_s: float = 180.0) -> tuple[bool, str]:
    import httpx

    url = f"http://127.0.0.1:{port}{path}"
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                return True, f"{url} OK"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(3.0)
    return False, f"{url} failed: {last_error}"


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
            return 1
        print(f"SKIP: {message}")
        return 0
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1

    print("Starting Postgres compose stack...")
    up = _run(["docker", "compose", "-f", str(COMPOSE), "up", "-d", "--build"], check=False)
    if up.returncode != 0:
        print(up.stderr or up.stdout, file=sys.stderr)
        return up.returncode

    failed: list[str] = []
    try:
        ok, message = _wait_for_health(8000, "/ready")
        print(message)
        if not ok:
            failed.append("registry")
        if not failed:
            import httpx

            status = httpx.get("http://127.0.0.1:8000/audit/status", timeout=10.0)
            if status.status_code != 200:
                failed.append("audit_status")
            else:
                print(f"audit/status OK: {status.json().get('event_count', 0)} events")
        if failed:
            logs = _run(["docker", "compose", "-f", str(COMPOSE), "logs", "--tail", "100"], check=False)
            print(logs.stdout or logs.stderr, file=sys.stderr)
            print(f"Postgres compose smoke failed: {', '.join(failed)}", file=sys.stderr)
            return 1
        print("Postgres compose smoke OK")
        return 0
    finally:
        _run(["docker", "compose", "-f", str(COMPOSE), "down", "-v"], check=False)


if __name__ == "__main__":
    sys.exit(main())
