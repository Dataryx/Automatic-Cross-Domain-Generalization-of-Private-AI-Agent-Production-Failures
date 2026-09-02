"""Idempotency ledger for audit sink batches (SIEM replay protection)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cfi_core.jcs import digest_hex


def compute_audit_batch_id(
    *,
    watermark_before: int,
    watermark_after: int,
    events: list[dict[str, Any]],
) -> str:
    """Stable batch id for a flush window; included in signed payloads."""
    return digest_hex(
        {
            "watermark_before": watermark_before,
            "watermark_after": watermark_after,
            "event_count": len(events),
            "events": events,
        }
    )


class AuditIdempotencyLedger:
    """Append-only ledger of flushed batch ids; optional file persistence."""

    def __init__(self, persist_path: Path | None = None) -> None:
        self._path = persist_path
        self._seen: set[str] = set()
        if persist_path is not None and persist_path.exists():
            for line in persist_path.read_text(encoding="utf-8").splitlines():
                batch_id = line.strip()
                if batch_id:
                    self._seen.add(batch_id)

    @classmethod
    def from_env(cls) -> AuditIdempotencyLedger | None:
        if os.getenv("CFI_AUDIT_SINK_IDEMPOTENCY", "0") != "1":
            return None
        path = os.getenv("CFI_AUDIT_SINK_IDEMPOTENCY_PATH")
        return cls(persist_path=Path(path) if path else None)

    def has(self, batch_id: str) -> bool:
        return batch_id in self._seen

    def record(self, batch_id: str) -> bool:
        """Record batch id; returns False if already present."""
        if batch_id in self._seen:
            return False
        self._seen.add(batch_id)
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(batch_id + "\n")
        return True
