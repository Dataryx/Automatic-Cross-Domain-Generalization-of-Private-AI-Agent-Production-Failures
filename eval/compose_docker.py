"""Docker Compose helpers for integration smoke scripts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def docker_available(*, require: bool = False) -> bool:
    """Return True when Docker is usable; skip or fail when require=False/True."""
    if shutil.which("docker") is None:
        message = "Docker not available"
        if require:
            print(message, file=sys.stderr)
            return False
        print(f"SKIP: {message}")
        return False
    daemon = subprocess.run(["docker", "info"], capture_output=True, text=True)
    if daemon.returncode != 0:
        message = "Docker daemon not running"
        if require:
            print(message, file=sys.stderr)
            return False
        print(f"SKIP: {message}")
        return False
    return True


def require_docker_enabled() -> bool:
    return os.getenv("CFI_REQUIRE_DOCKER", "0") == "1"


def run_compose(cmd: list[str], *, compose_file: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=False, text=True, capture_output=True)


def wait_for_url(
    url: str,
    *,
    timeout_s: float = 180.0,
    interval_s: float = 2.0,
    verify: bool | str | None = None,
    use_client_cert: bool = True,
) -> tuple[bool, str]:
    import httpx

    from cfi_core.http_tls import httpx_client_options

    if not use_client_cert:
        request_opts = {"verify": False if verify is None else verify}
    elif verify is None:
        request_opts = httpx_client_options()
    else:
        request_opts = {**httpx_client_options(), "verify": verify}
    deadline = time.time() + timeout_s
    last_error = ""
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=5.0, **request_opts)
            if response.status_code == 200:
                return True, f"{url} OK"
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(interval_s)
    return False, f"{url} failed: {last_error}"


def compose_up(compose_file: Path) -> int:
    up = run_compose(["docker", "compose", "-f", str(compose_file), "up", "-d", "--build"], compose_file=compose_file)
    if up.returncode != 0:
        print(up.stderr or up.stdout, file=sys.stderr)
    return up.returncode


def compose_down(compose_file: Path) -> None:
    down = run_compose(["docker", "compose", "-f", str(compose_file), "down", "-v"], compose_file=compose_file)
    if down.returncode != 0:
        print(down.stderr or down.stdout, file=sys.stderr)


def compose_logs(compose_file: Path, *, tail: int = 80) -> str:
    logs = run_compose(
        ["docker", "compose", "-f", str(compose_file), "logs", f"--tail={tail}"],
        compose_file=compose_file,
    )
    return logs.stdout or logs.stderr
