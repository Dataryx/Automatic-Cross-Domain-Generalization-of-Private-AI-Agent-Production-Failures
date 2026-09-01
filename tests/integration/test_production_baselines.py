"""Computed production baseline tests."""

from eval.production.baselines import BASELINE_RUNNERS
from eval.production.harness import run_baseline


def test_all_stub_baselines_are_computed() -> None:
    for name in [
        "raw_incident_replay",
        "pii_redacted_narrative",
        "taxonomy_label_guidance",
        "embedding_retrieval",
        "manual_metamorphic",
    ]:
        assert name in BASELINE_RUNNERS
        result = run_baseline(name, {"spec_id": "t", "cohort_id": "c", "domain": "procurement"})
        assert "placeholder" not in " ".join(result.assumptions).lower()


def test_raw_incident_higher_risk_than_cfi() -> None:
    raw = run_baseline("raw_incident_replay", {"spec_id": "t", "cohort_id": "c"})
    privacy = run_baseline("pii_redacted_narrative", {"spec_id": "t", "cohort_id": "c"})
    assert raw.value >= privacy.value
