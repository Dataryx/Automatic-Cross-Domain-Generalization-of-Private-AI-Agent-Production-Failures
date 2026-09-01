"""External audit sink for governance event export."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AuditSinkResult:
    file_path: str | None = None
    file_appended: int = 0
    webhook_url: str | None = None
    webhook_status: int | None = None
    webhook_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_appended": self.file_appended,
            "webhook_url": self.webhook_url,
            "webhook_status": self.webhook_status,
            "webhook_error": self.webhook_error,
        }


class AuditSink:
    """Append audit events to a local file and/or POST to an external webhook."""

    def __init__(self, file_path: Path | None = None, webhook_url: str | None = None) -> None:
        self._file_path = file_path
        self._webhook_url = webhook_url

    @classmethod
    def from_env(cls) -> AuditSink | None:
        file_path = os.getenv("CFI_AUDIT_SINK_PATH")
        webhook_url = os.getenv("CFI_AUDIT_SINK_URL")
        if not file_path and not webhook_url:
            return None
        return cls(
            file_path=Path(file_path) if file_path else None,
            webhook_url=webhook_url,
        )

    def emit(self, events: list[dict[str, Any]]) -> AuditSinkResult:
        result = AuditSinkResult(
            file_path=str(self._file_path) if self._file_path else None,
            webhook_url=self._webhook_url,
        )
        if self._file_path is not None:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            with self._file_path.open("a", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
            result.file_appended = len(events)
        if self._webhook_url and events:
            try:
                import httpx

                response = httpx.post(
                    self._webhook_url,
                    json={"events": events, "source": "cfi-fed-registry"},
                    timeout=10.0,
                )
                result.webhook_status = response.status_code
            except Exception as exc:
                result.webhook_error = str(exc)
        return result


def flush_audit_events(
    sink: AuditSink | None,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Export audit events to configured external sink(s)."""
    if sink is None:
        return {
            "flushed": False,
            "reason": "no_sink_configured",
            "event_count": len(events),
        }
    result = sink.emit(events)
    return {
        "flushed": True,
        "event_count": len(events),
        **result.to_dict(),
    }
