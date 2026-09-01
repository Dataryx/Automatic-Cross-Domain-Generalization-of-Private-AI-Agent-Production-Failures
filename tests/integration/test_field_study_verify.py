"""Field study verification script tests."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "verify_field_study.py"


def test_field_study_verification_passes() -> None:
    result = subprocess.run([sys.executable, str(VERIFY)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Field study verification OK" in result.stdout
