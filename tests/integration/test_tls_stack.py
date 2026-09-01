"""TLS stack artifact tests."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tls_stack_verification() -> None:
    script = ROOT / "scripts" / "verify_tls_stack.py"
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "TLS stack verification OK" in result.stdout
