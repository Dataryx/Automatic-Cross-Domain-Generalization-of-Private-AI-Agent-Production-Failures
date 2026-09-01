"""Audit sink unit tests."""

import json
from pathlib import Path

from cfi_governance.audit_sink import AuditSink, flush_audit_events


def test_file_sink_appends_ndjson(tmp_path: Path) -> None:
    sink_path = tmp_path / "audit.ndjson"
    sink = AuditSink(file_path=sink_path)
    events = [{"action": "cfi.registered", "resource_id": "cfi-1"}]
    result = sink.emit(events)
    assert result.file_appended == 1
    line = json.loads(sink_path.read_text(encoding="utf-8").strip())
    assert line["action"] == "cfi.registered"


def test_flush_without_sink_reports_not_configured() -> None:
    result = flush_audit_events(None, [{"action": "noop"}])
    assert result["flushed"] is False
    assert result["reason"] == "no_sink_configured"
    assert result["event_count"] == 1
