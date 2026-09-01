"""Tracing configuration tests."""

from cfi_core.tracing import configure_tracing, tracing_status


def test_tracing_status_without_endpoint() -> None:
    status = tracing_status()
    assert "endpoint_configured" in status
    assert status["provider_active"] is False


def test_configure_tracing_noop_without_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("CFI_OTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert configure_tracing("test-service") is False
