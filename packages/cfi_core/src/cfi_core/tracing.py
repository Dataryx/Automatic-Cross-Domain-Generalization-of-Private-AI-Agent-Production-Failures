"""OpenTelemetry exporter wiring (optional; requires otel extra)."""

from __future__ import annotations

import os


def configure_tracing(service: str) -> bool:
    """Configure OTLP HTTP exporter when endpoint env is set.

    Returns True when a tracer provider was installed.
    """
    endpoint = os.getenv("CFI_OTEL_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-not-found]
    except ImportError:
        return False

    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return True


def tracing_status() -> dict[str, str | bool]:
    configured = bool(os.getenv("CFI_OTEL_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
    active = False
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        active = provider.__class__.__name__ != "ProxyTracerProvider"
    except Exception:
        active = False
    return {
        "endpoint_configured": configured,
        "provider_active": active,
    }
