#!/usr/bin/env python3
"""Aggregate pipeline smoke summaries into eval/output/pipeline_matrix.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "output"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfi_contributor.pipeline_runner import run_inprocess_full_pipeline
from eval.pipeline_matrix import validate_matrix, write_pipeline_matrix


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    inprocess_path = OUT / "full_pipeline_summary.json"
    if not inprocess_path.exists():
        summary = run_inprocess_full_pipeline()
        inprocess_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    matrix = write_pipeline_matrix(OUT)
    errors = validate_matrix(matrix, require_inprocess=True)
    if errors:
        print("; ".join(errors), file=sys.stderr)
        return 1

    print(
        f"Pipeline matrix OK: {matrix['ok_count']}/{matrix['total_variants']} variants present "
        f"(inprocess required)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
