"""Append-only governance audit log for registry actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEvent:
    timestamp: str
    actor: str
    action: str
    resource_id: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "resource_id": self.resource_id,
            "detail": self.detail,
        }


class AuditLog:
    """In-memory append-only audit trail (export for compliance review)."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, actor: str, action: str, resource_id: str, detail: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            resource_id=resource_id,
            detail=detail or {},
        )
        self._events.append(event)
        return event

    def export(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._events]

    def __len__(self) -> int:
        return len(self._events)
