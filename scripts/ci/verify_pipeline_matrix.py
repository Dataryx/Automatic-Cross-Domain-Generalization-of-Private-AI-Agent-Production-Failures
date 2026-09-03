#!/usr/bin/env python3
"""Aggregate pipeline smoke summaries into tools/evaluation/output/pipeline_matrix.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1]
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
import pathsetup

ROOT = pathsetup.ROOT
OUT = ROOT / "tools/evaluation" / "output"

from cfi_contributor.pipeline_runner import run_inprocess_full_pipeline
from pipeline_matrix import PIPELINE_VARIANTS, validate_matrix, write_pipeline_matrix


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    inprocess_path = OUT / "full_pipeline_summary.json"
    if not inprocess_path.exists():
        summary = run_inprocess_full_pipeline()
        inprocess_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    matrix = write_pipeline_matrix(OUT)
    require_all = os.getenv("CFI_PIPELINE_REQUIRE_ALL", "0") == "1"
    errors = validate_matrix(matrix, require_inprocess=True, require_all=require_all)
    if errors:
        print("; ".join(errors), file=sys.stderr)
        return 1

    label = "all variants" if require_all else "inprocess required"
    print(
        f"Pipeline matrix OK: {matrix['ok_count']}/{matrix['total_variants']} variants present ({label})"
    )
    if require_all and matrix["ok_count"] < len(PIPELINE_VARIANTS):
        print("Not all pipeline variants present", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
