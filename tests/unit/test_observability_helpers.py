"""Observability helper tests."""

from cfi_core.observability import format_prometheus, service_health
from cfi_federation.accountant import PrivacyAccountant


def test_format_prometheus_renders_gauges() -> None:
    text = format_prometheus({"cfi_up": 1.0}, help_text={"cfi_up": "Service up"})
    assert "cfi_up 1.0" in text
    assert "# TYPE cfi_up gauge" in text


def test_service_health_payload() -> None:
    payload = service_health("registry")
    assert payload["service"] == "registry"
    assert payload["status"] == "ok"


def test_accountant_snapshot() -> None:
    accountant = PrivacyAccountant(total_epsilon=10.0, min_cohort_for_slice=2)
    verdict = accountant.request_release(1.0, 5, "cohort-a", "epoch-1")
    assert verdict.allowed
    snap = accountant.snapshot()
    assert snap["remaining_epsilon"] == 9.0
    assert snap["release_count"] == 1
