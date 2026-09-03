#!/usr/bin/env python3
"""Phase 6 prospective field-study pilot (compressed simulation).

Does NOT operate a live six-month network. Validates reporting criteria,
anti-survivorship inclusion, and lead-time measurement plumbing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cfi_governance.field_study import FieldStudyConfig, run_prospective_study

SEED = 421337
OUT = Path(__file__).resolve().parent / "output"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result = run_prospective_study(FieldStudyConfig(duration_days=180, org_count=8, seed=SEED))

    summary = {
        "seed": SEED,
        "duration_days": result.duration_days,
        "org_count": result.org_count,
        "total_reports": result.total_reports,
        "cfi_releases": result.cfi_releases,
        "failed_extractions": result.failed_extractions,
        "non_shareable": result.non_shareable,
        "production_incidents": result.production_incidents,
        "susceptible_before_incident": result.susceptible_before_incident,
        "prevention_rate": result.prevention_rate,
        "lead_time_median_days": result.lead_time_median_days,
        "assumptions": result.assumptions,
    }
    (OUT / "field_study_summary.json").write_text(json.dumps(summary, indent=2))
    (OUT / "field_reports.json").write_text(
        json.dumps(
            [
                {
                    "org_id": r.org_id,
                    "day": r.day,
                    "type": r.report_type.value,
                    "invariant_id": r.invariant_id,
                    "susceptible": r.susceptible,
                    "notes": r.notes,
                }
                for r in result.reports
            ],
            indent=2,
        )
    )

    print(f"Field study: {result.duration_days}d, {result.org_count} orgs, {result.total_reports} reports")
    print(f"  CFI releases: {result.cfi_releases} (failed={result.failed_extractions}, non-shareable={result.non_shareable})")
    print(f"  Prevention signal: {result.susceptible_before_incident}/{result.production_incidents} incidents flagged early")
    if result.lead_time_median_days is not None:
        print(f"  Median lead time: {result.lead_time_median_days:.0f} days")
    print("Assumptions:")
    for a in result.assumptions:
        print(f"  - {a}")

    if result.failed_extractions + result.non_shareable == 0:
        print("WARNING: anti-survivorship rule requires failed/non-shareable reports", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
