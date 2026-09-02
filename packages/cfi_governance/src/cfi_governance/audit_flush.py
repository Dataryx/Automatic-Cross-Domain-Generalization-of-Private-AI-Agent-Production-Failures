"""Build signed audit batches for sink flush."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from cfi_governance.audit_attestation import sign_audit_export
from cfi_governance.audit_idempotency import compute_audit_batch_id


def sign_audit_flush_batch(
    events: list[dict[str, Any]],
    *,
    watermark_before: int,
    watermark_after: int,
) -> dict[str, Any]:
    batch_id = compute_audit_batch_id(
        watermark_before=watermark_before,
        watermark_after=watermark_after,
        events=events,
    )
    return sign_audit_export(
        {
            "batch_id": batch_id,
            "events": events,
            "watermark_before": watermark_before,
            "watermark_after": watermark_after,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "assumptions": [
                "Signed batch covers incremental flush only.",
                "batch_id enables SIEM idempotency; not a WORM store by itself.",
                "Enable CFI_AUDIT_SINK_WORM for append-only hash chain on local file sink.",
            ],
        }
    )
