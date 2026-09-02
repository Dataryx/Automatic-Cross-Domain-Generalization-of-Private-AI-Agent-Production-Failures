"""External audit sink for governance event export."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cfi_governance.audit_idempotency import AuditIdempotencyLedger, compute_audit_batch_id
from cfi_governance.audit_worm import read_worm_chain_head, wrap_worm_record


@dataclass
class AuditSinkResult:
    file_path: str | None = None
    file_appended: int = 0
    signed_batch: bool = False
    batch_id: str | None = None
    idempotent_skip: bool = False
    worm_chain: bool = False
    webhook_url: str | None = None
    webhook_status: int | None = None
    webhook_attempts: int = 0
    webhook_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_appended": self.file_appended,
            "signed_batch": self.signed_batch,
            "batch_id": self.batch_id,
            "idempotent_skip": self.idempotent_skip,
            "worm_chain": self.worm_chain,
            "webhook_url": self.webhook_url,
            "webhook_status": self.webhook_status,
            "webhook_attempts": self.webhook_attempts,
            "webhook_error": self.webhook_error,
        }


class AuditSink:
    """Append audit events to a local file and/or POST to an external webhook."""

    def __init__(
        self,
        file_path: Path | None = None,
        webhook_url: str | None = None,
        max_retries: int | None = None,
        idempotency: AuditIdempotencyLedger | None = None,
        worm_chain: bool | None = None,
    ) -> None:
        self._file_path = file_path
        self._webhook_url = webhook_url
        self._max_retries = max_retries if max_retries is not None else int(os.getenv("CFI_AUDIT_SINK_RETRIES", "3"))
        self._idempotency = idempotency if idempotency is not None else AuditIdempotencyLedger.from_env()
        if worm_chain is None:
            worm_chain = os.getenv("CFI_AUDIT_SINK_WORM", "0") == "1"
        self._worm_chain = worm_chain

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

    def _resolve_batch_id(
        self,
        events: list[dict[str, Any]],
        signed_batch: dict[str, Any] | None,
    ) -> str | None:
        if signed_batch is not None:
            return str(signed_batch.get("batch_id", "")) or None
        if not events:
            return None
        return compute_audit_batch_id(
            watermark_before=-1,
            watermark_after=len(events),
            events=events,
        )

    def _post_webhook(self, payload: dict[str, Any], batch_id: str | None) -> tuple[int | None, int, str | None]:
        import httpx

        headers: dict[str, str] = {}
        if batch_id:
            headers["X-CFI-Batch-Id"] = batch_id
            headers["Idempotency-Key"] = batch_id

        last_error: str | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = httpx.post(
                    self._webhook_url or "",
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code < 500:
                    return response.status_code, attempt, None
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < self._max_retries:
                time.sleep(0.25 * (2 ** (attempt - 1)))
        return None, self._max_retries, last_error

    def _write_file_line(self, payload: dict[str, Any]) -> None:
        assert self._file_path is not None
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if self._worm_chain:
            previous_hash = read_worm_chain_head(self._file_path)
            record = wrap_worm_record(payload, previous_hash=previous_hash)
            line = json.dumps(record, sort_keys=True)
        else:
            line = json.dumps(payload, sort_keys=True)
        with self._file_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def emit(
        self,
        events: list[dict[str, Any]],
        signed_batch: dict[str, Any] | None = None,
    ) -> AuditSinkResult:
        batch_id = self._resolve_batch_id(events, signed_batch)
        result = AuditSinkResult(
            file_path=str(self._file_path) if self._file_path else None,
            webhook_url=self._webhook_url,
            signed_batch=signed_batch is not None,
            batch_id=batch_id,
            worm_chain=self._worm_chain,
        )
        if batch_id and self._idempotency is not None and self._idempotency.has(batch_id):
            result.idempotent_skip = True
            return result

        payload = signed_batch if signed_batch is not None else {"events": events, "source": "cfi-fed-registry"}
        if batch_id and signed_batch is None:
            payload = {**payload, "batch_id": batch_id}

        if self._file_path is not None:
            if signed_batch is not None:
                self._write_file_line(signed_batch)
                result.file_appended = 1
            else:
                for event in events:
                    self._write_file_line(event)
                result.file_appended = len(events)

        if self._webhook_url and (signed_batch is not None or events):
            status, attempts, error = self._post_webhook(payload, batch_id)
            result.webhook_status = status
            result.webhook_attempts = attempts
            result.webhook_error = error

        if batch_id and self._idempotency is not None:
            self._idempotency.record(batch_id)

        return result


def flush_audit_events(
    sink: AuditSink | None,
    events: list[dict[str, Any]],
    signed_batch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Export audit events to configured external sink(s)."""
    if sink is None:
        return {
            "flushed": False,
            "reason": "no_sink_configured",
            "event_count": len(events),
            "signed_batch": signed_batch is not None,
        }
    result = sink.emit(events, signed_batch=signed_batch)
    return {
        "flushed": bool(events),
        "event_count": len(events),
        "signed_batch": signed_batch is not None,
        **result.to_dict(),
    }
