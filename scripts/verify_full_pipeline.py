#!/usr/bin/env python3
"""Full CFI-Fed pipeline: publish -> assess -> federate -> consortium round."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfi_contributor.pipeline_runner import run_inprocess_full_pipeline


def main() -> int:
    try:
        summary = run_inprocess_full_pipeline()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    out = ROOT / "eval" / "output"
    out.mkdir(parents=True, exist_ok=True)
    (out / "full_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Full pipeline OK: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
