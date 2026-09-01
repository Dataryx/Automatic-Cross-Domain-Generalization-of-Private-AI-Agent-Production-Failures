#!/usr/bin/env python3
"""Verify Section 9 sim metrics within tolerance (seed 421337)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "sim" / "run_cfi_sim.py"
OUT = ROOT / "sim" / "output" / "q1_lodo_summary.csv"
VERIFY_FIGURES = ROOT / "scripts" / "verify_figures.py"


def main() -> int:
    if not OUT.exists():
        print("Running sim study (seed 421337)...")
        result = subprocess.run([sys.executable, str(SIM)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    else:
        # Re-run to validate assertions embedded in sim script
        result = subprocess.run([sys.executable, str(SIM)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    fig = subprocess.run([sys.executable, str(VERIFY_FIGURES)], cwd=ROOT)
    if fig.returncode != 0:
        return fig.returncode
    print(f"Sim verification OK: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
