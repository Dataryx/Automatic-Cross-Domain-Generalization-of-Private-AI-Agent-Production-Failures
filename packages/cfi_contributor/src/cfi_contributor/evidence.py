"""Telemetry-format agnostic evidence adapter with local artifact digests."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from cfi_core.models import EventType
from cfi_core.wire import TraceEvent, TypedTrace


@dataclass
class NormalizedRecord:
    event: TraceEvent
    local_artifact_pointer: str
    digest: str


class EvidenceAdapter(ABC):
    @abstractmethod
    def normalize(self, raw: Any) -> list[NormalizedRecord]:
        ...


def _digest(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class OpenTelemetryAdapter(EvidenceAdapter):
    """Ingest OpenTelemetry-compatible spans."""

    def normalize(self, raw: list[dict[str, Any]]) -> list[NormalizedRecord]:
        records: list[NormalizedRecord] = []
        for idx, span in enumerate(raw):
            name = span.get("name", "unknown")
            event_type = _map_span_name(name)
            attrs = span.get("attributes", {})
            pointer = span.get("artifact_ref", f"otel://span/{span.get('span_id', idx)}")
            event = TraceEvent(
                event_type=event_type,
                actor=str(attrs.get("actor", "unknown")),
                inputs={k: v for k, v in attrs.items() if k.startswith("input.")},
                outputs={k: v for k, v in attrs.items() if k.startswith("output.")},
                state_before=str(attrs.get("state.before", "unknown")),
                state_after=str(attrs.get("state.after", "unknown")),
                provenance_label=str(span.get("trace_id", "")),
                artifact_digest=_digest(span),
                sequence_index=int(attrs.get("sequence", idx)),
                concurrent_with=list(attrs.get("concurrent_with", [])),
            )
            records.append(NormalizedRecord(event=event, local_artifact_pointer=pointer, digest=event.artifact_digest))
        return records


class JsonTraceAdapter(EvidenceAdapter):
    """Second non-OTel format: simple JSON event list."""

    def normalize(self, raw: dict[str, Any]) -> list[NormalizedRecord]:
        records: list[NormalizedRecord] = []
        for idx, ev in enumerate(raw.get("events", [])):
            et = EventType(ev.get("type", "observation"))
            pointer = ev.get("ref", f"json://event/{idx}")
            event = TraceEvent(
                event_type=et,
                actor=str(ev.get("actor", "unknown")),
                inputs=ev.get("inputs", {}),
                outputs=ev.get("outputs", {}),
                state_before=str(ev.get("state_before", "unknown")),
                state_after=str(ev.get("state_after", "unknown")),
                provenance_label=str(ev.get("label", "")),
                artifact_digest=_digest(ev),
                sequence_index=int(ev.get("index", idx)),
                concurrent_with=list(ev.get("concurrent_with", [])),
            )
            records.append(NormalizedRecord(event=event, local_artifact_pointer=pointer, digest=event.artifact_digest))
        return records


def _map_span_name(name: str) -> EventType:
    mapping = {
        "policy.lookup": EventType.POLICY_LOOKUP,
        "tool.call": EventType.TOOL_CALL,
        "decision": EventType.DECISION,
        "action": EventType.ACTION,
        "approval": EventType.APPROVAL,
        "state.mutation": EventType.STATE_MUTATION,
        "compensation": EventType.COMPENSATION,
        "termination": EventType.TERMINATION,
    }
    return mapping.get(name, EventType.OBSERVATION)


def build_typed_trace(records: list[NormalizedRecord]) -> TypedTrace:
    return TypedTrace(events=[r.event for r in records])
