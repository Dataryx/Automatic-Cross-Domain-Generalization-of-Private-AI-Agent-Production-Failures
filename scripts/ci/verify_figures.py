#!/usr/bin/env python3
"""Verify Section 9 sim figures exist and are non-empty (seed 421337)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "tools" / "feasibility" / "output" / "figures"
META = ROOT / "tools" / "feasibility" / "output" / "study_meta.json"

EXPECTED_STEMS = [
    "fig1_lodo_f1",
    "fig2_corruption",
    "fig3_privacy",
    "fig4_compilation",
    "fig5_dp",
    "fig6_cfi_graph",
    "fig7_architecture",
    "fig8_threat_model",
]
MIN_BYTES = 1024


def verify() -> list[str]:
    errors: list[str] = []
    if not META.exists():
        errors.append(f"missing study metadata: {META}")
    else:
        meta = json.loads(META.read_text(encoding="utf-8"))
        if meta.get("seed") != 421337:
            errors.append(f"unexpected seed in study_meta.json: {meta.get('seed')}")

    if not FIG_DIR.exists():
        errors.append(f"missing figures directory: {FIG_DIR}")
        return errors

    for stem in EXPECTED_STEMS:
        for ext in ("pdf", "png"):
            path = FIG_DIR / f"{stem}.{ext}"
            if not path.exists():
                errors.append(f"missing figure: {path.name}")
                continue
            size = path.stat().st_size
            if size < MIN_BYTES:
                errors.append(f"figure too small ({size} B): {path.name}")
    return errors


def main() -> int:
    errors = verify()
    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print(f"Figure verification OK: {len(EXPECTED_STEMS)} figures x 2 formats in {FIG_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
