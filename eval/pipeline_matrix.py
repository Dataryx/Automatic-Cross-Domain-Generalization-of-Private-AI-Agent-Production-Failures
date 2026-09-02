"""Collect and validate CFI-Fed pipeline smoke summaries across deployment variants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PIPELINE_VARIANTS: dict[str, str] = {
    "inprocess": "full_pipeline_summary.json",
    "compose": "compose_full_pipeline_summary.json",
    "postgres_compose": "postgres_compose_full_pipeline_summary.json",
    "tls": "tls_full_pipeline_summary.json",
    "mtls": "mtls_full_pipeline_summary.json",
    "postgres_tls": "postgres_tls_full_pipeline_summary.json",
    "mtls_required": "mtls_required_full_pipeline_summary.json",
}

REQUIRED_SUMMARY_KEYS = ("invariant_id", "assessed", "aggregate_prevalence", "consortium_prevalence")


def _variant_status(summary: dict[str, Any] | None) -> str:
    if summary is None:
        return "missing"
    if summary.get("status") == "missing":
        return "missing"
    if all(key in summary for key in REQUIRED_SUMMARY_KEYS):
        return "ok"
    return "invalid"


def collect_pipeline_matrix(output_dir: Path) -> dict[str, Any]:
    variants: dict[str, Any] = {}
    for name, filename in PIPELINE_VARIANTS.items():
        path = output_dir / filename
        if not path.exists():
            variants[name] = {"status": "missing", "summary_file": filename}
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        variants[name] = {
            "status": _variant_status(summary),
            "summary_file": filename,
            "summary": summary,
        }

    ok_count = sum(1 for item in variants.values() if item["status"] == "ok")
    return {
        "variants": variants,
        "ok_count": ok_count,
        "total_variants": len(PIPELINE_VARIANTS),
        "assumptions": [
            "Pipeline matrix aggregates smoke summaries; missing docker variants are expected locally.",
            "Only inprocess variant is required for CI without Docker.",
        ],
    }


def write_pipeline_matrix(output_dir: Path, *, matrix_path: Path | None = None) -> dict[str, Any]:
    matrix = collect_pipeline_matrix(output_dir)
    target = matrix_path or (output_dir / "pipeline_matrix.json")
    target.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    return matrix


def validate_matrix(
    matrix: dict[str, Any],
    *,
    require_inprocess: bool = True,
    require_all: bool = False,
    required_variants: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    variants = matrix.get("variants", {})
    if require_inprocess:
        inprocess = variants.get("inprocess", {})
        if inprocess.get("status") != "ok":
            errors.append("inprocess pipeline summary missing or invalid")
    targets = set(required_variants or [])
    if require_all:
        targets = set(PIPELINE_VARIANTS.keys())
    for name in sorted(targets):
        item = variants.get(name, {})
        if item.get("status") != "ok":
            errors.append(f"{name} pipeline summary missing or invalid")
    for name, item in variants.items():
        if item.get("status") == "invalid":
            errors.append(f"{name} pipeline summary invalid")
    return errors
