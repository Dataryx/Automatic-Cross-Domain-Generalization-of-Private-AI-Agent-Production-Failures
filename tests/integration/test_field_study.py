"""Phase 6 field study tests."""

from cfi_governance.field_study import FieldStudyConfig, ReportType, run_prospective_study


def test_field_study_includes_survivorship_reports() -> None:
    result = run_prospective_study(FieldStudyConfig(duration_days=90, org_count=8, seed=421337))
    assert result.failed_extractions + result.non_shareable > 0
    assert result.cfi_releases > 0


def test_field_study_tracks_recipient_evaluations() -> None:
    result = run_prospective_study(FieldStudyConfig(duration_days=120, org_count=4, seed=1))
    evals = [r for r in result.reports if r.report_type == ReportType.RECIPIENT_EVALUATION]
    assert len(evals) > 0
    assert any(r.susceptible for r in evals)


def test_field_study_deterministic_with_seed() -> None:
    a = run_prospective_study(FieldStudyConfig(seed=421337))
    b = run_prospective_study(FieldStudyConfig(seed=421337))
    assert a.cfi_releases == b.cfi_releases
    assert a.total_reports == b.total_reports
