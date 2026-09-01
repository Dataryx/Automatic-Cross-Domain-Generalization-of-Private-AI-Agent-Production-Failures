#!/usr/bin/env python3
"""Build release manifest with DoD status and test summary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "output"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    from eval.verify_dod import verify

    dod = verify()
    test = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    last_line = (test.stdout or "").strip().splitlines()[-1] if test.stdout else ""
    manifest = {
        "package": "cfi-fed",
        "version": "0.1.0",
        "dod": dod.to_dict(),
        "pytest_exit_code": test.returncode,
        "pytest_summary": last_line,
        "assumptions": [
            "Release manifest is a research prototype checkpoint, not a production attestation.",
            "Re-run eval/run_all.py before external distribution.",
        ],
    }
    path = OUT / "release_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Release manifest written to {path}")
    print(f"DoD: {dod.to_dict()['passed']}/{dod.to_dict()['total']} | pytest: {last_line}")
    return 0 if dod.all_passed and test.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
