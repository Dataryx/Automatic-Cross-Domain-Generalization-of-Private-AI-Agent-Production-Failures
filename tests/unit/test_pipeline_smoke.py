"""Pipeline smoke manifest tests."""

from cfi_core.examples import build_exception_precedence_cfi
from pipeline_smoke import cohort_manifest


def test_cohort_manifest_epoch() -> None:
    invariant_id = build_exception_precedence_cfi().id
    manifest = cohort_manifest(invariant_id, epoch="test-epoch")
    assert manifest.invariant_id == invariant_id
    assert manifest.aggregation_epoch == "test-epoch"
    assert manifest.measurement_spec.spec_id == "test-epoch"
    assert manifest.minimum_cohort_k == 5
