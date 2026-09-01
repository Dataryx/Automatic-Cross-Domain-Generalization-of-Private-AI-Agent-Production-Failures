"""Production ablation baseline tests."""

from eval.production.harness import run_baseline


def test_cfi_ablations_differ_from_full() -> None:
    config = {"spec_id": "test", "cohort_id": "c1", "domain": "procurement"}
    full = run_baseline("cfi_no_minimization", config)
    no_nc = run_baseline("cfi_no_negative_controls", config)
    no_canon = run_baseline("cfi_no_canonicalization", config)
    assert no_canon.value == 0.0
    assert no_nc.metric == "coverage_without_negative_controls"
    assert full.value <= 1.0
