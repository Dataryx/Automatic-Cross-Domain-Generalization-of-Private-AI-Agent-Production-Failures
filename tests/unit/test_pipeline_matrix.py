"""Pipeline matrix aggregation tests."""

import json
from pathlib import Path

from eval.pipeline_matrix import collect_pipeline_matrix, validate_matrix, write_pipeline_matrix


def test_collect_pipeline_matrix_inprocess(tmp_path: Path) -> None:
    summary = {
        "invariant_id": "CFI-TEST-0001",
        "assessed": True,
        "aggregate_prevalence": 1.0,
        "consortium_prevalence": 1.0,
    }
    (tmp_path / "full_pipeline_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    matrix = collect_pipeline_matrix(tmp_path)
    assert matrix["variants"]["inprocess"]["status"] == "ok"
    assert matrix["variants"]["compose"]["status"] == "missing"
    assert matrix["ok_count"] == 1


def test_write_and_validate_matrix(tmp_path: Path) -> None:
    summary = {
        "invariant_id": "CFI-TEST-0001",
        "assessed": True,
        "aggregate_prevalence": 1.0,
        "consortium_prevalence": 1.0,
    }
    (tmp_path / "full_pipeline_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    matrix = write_pipeline_matrix(tmp_path)
    assert (tmp_path / "pipeline_matrix.json").exists()
    assert validate_matrix(matrix) == []
