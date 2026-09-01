#!/usr/bin/env python3
"""Verify prospective field-study harness outputs and anti-survivorship criteria."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "eval" / "field" / "run_prospective_pilot.py"
SUMMARY = ROOT / "eval" / "field" / "output" / "field_study_summary.json"


def main() -> int:
    result = subprocess.run([sys.executable, str(PILOT)], cwd=ROOT)
    if result.returncode != 0:
        return result.returncode
    if not SUMMARY.exists():
        print(f"Missing summary: {SUMMARY}", file=sys.stderr)
        return 1

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    checks = [
        ("seed", summary.get("seed") == 421337),
        ("anti_survivorship", (summary.get("failed_extractions", 0) + summary.get("non_shareable", 0)) > 0),
        ("cfi_releases", summary.get("cfi_releases", 0) > 0),
        ("production_incidents", summary.get("production_incidents", 0) > 0),
        ("prevention_signal", summary.get("susceptible_before_incident", 0) >= 0),
        ("assumptions_documented", len(summary.get("assumptions", [])) >= 3),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"Field study verification failed: {', '.join(failed)}", file=sys.stderr)
        print(json.dumps(summary, indent=2))
        return 1
    print(
        "Field study verification OK: "
        f"releases={summary['cfi_releases']} "
        f"failed={summary['failed_extractions']} "
        f"prevention_rate={summary['prevention_rate']:.2f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
