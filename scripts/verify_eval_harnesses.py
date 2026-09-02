#!/usr/bin/env python3
"""Run consortium, redteam, production, and corpus eval harnesses."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HARNESS = [
    ("consortium_pilot", [sys.executable, "eval/consortium/run_consortium_pilot.py"]),
    ("redteam", [sys.executable, "eval/redteam/run_redteam.py"]),
    ("production_harness", [sys.executable, "eval/production/harness.py"]),
    ("corpus_benchmark", [sys.executable, "eval/benchmarks/run_corpus.py"]),
]


def main() -> int:
    failed: list[str] = []
    for name, cmd in HARNESS:
        print(f"\n=== {name} ===")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"\nEval harness failures: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nEval harness verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
