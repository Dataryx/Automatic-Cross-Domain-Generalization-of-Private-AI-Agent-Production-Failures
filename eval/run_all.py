#!/usr/bin/env python3
"""Run all evaluation harnesses in sequence."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("pytest", [sys.executable, "-m", "pytest", "tests/", "-q"]),
    ("verify_dod", [sys.executable, "eval/verify_dod.py"]),
    ("consortium_pilot", [sys.executable, "eval/consortium/run_consortium_pilot.py"]),
    ("field_pilot", [sys.executable, "eval/field/run_prospective_pilot.py"]),
    ("redteam", [sys.executable, "eval/redteam/run_redteam.py"]),
    ("production_harness", [sys.executable, "eval/production/harness.py"]),
    ("corpus_benchmark", [sys.executable, "eval/benchmarks/run_corpus.py"]),
    ("tau_adapter", [sys.executable, "eval/benchmarks/tau_adapter.py"]),
    ("golden_path", [sys.executable, "scripts/golden_path.py"]),
]


def main() -> int:
    failed: list[str] = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll evaluation steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
