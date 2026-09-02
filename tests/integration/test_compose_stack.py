"""Compose stack verification (skipped when Docker unavailable)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_compose_stack.py"


def _docker_daemon_ready() -> bool:
    result = subprocess.run(["docker", "info"], capture_output=True)
    return result.returncode == 0


def test_compose_stack_script_exists() -> None:
    assert SCRIPT.exists()


def test_compose_stack_smoke_when_docker_available() -> None:
    if shutil.which("docker") is None or not _docker_daemon_ready():
        return
    env = {**os.environ, "CFI_REQUIRE_DOCKER": "1"}
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, env=env)
    assert result.returncode == 0
