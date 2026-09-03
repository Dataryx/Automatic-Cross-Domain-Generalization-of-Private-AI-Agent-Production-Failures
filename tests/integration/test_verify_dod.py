"""Definition of Done verification tests."""

from verify_dod import verify


def test_dod_checks_pass() -> None:
    report = verify()
    assert report.all_passed, [c for c in report.checks if not c.passed]
