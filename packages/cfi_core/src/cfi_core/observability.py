"""Lightweight observability helpers (Prometheus text + optional OpenTelemetry spans)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator
from uuid import uuid4


def new_request_id() -> str:
    return uuid4().hex


def format_prometheus(metrics: dict[str, float], help_text: dict[str, str] | None = None) -> str:
    """Render gauge metrics in Prometheus exposition format."""
    lines: list[str] = []
    help_text = help_text or {}
    for name, value in metrics.items():
        if name in help_text:
            lines.append(f"# HELP {name} {help_text[name]}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[None]:
    """Best-effort trace span; no-op when OpenTelemetry is not configured."""
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("cfi-fed")
        with tracer.start_as_current_span(name, attributes=attributes or {}):
            yield
    except Exception:
        yield


def service_health(service: str, *, ready: bool = True) -> dict[str, str]:
    return {
        "status": "ok" if ready else "degraded",
        "service": service,
        "ready": str(ready).lower(),
    }
