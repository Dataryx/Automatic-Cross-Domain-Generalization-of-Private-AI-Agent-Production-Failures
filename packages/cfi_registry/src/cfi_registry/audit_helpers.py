"""Registry audit sink helpers."""

from __future__ import annotations

import os
from typing import Any


def maybe_signed_flush_batch(
    events: list[dict[str, Any]],
    *,
    watermark_before: int,
    watermark_after: int,
) -> dict[str, Any] | None:
    if not events or os.getenv("CFI_AUDIT_SINK_SIGNED", "0") != "1":
        return None
    from cfi_governance.audit_flush import sign_audit_flush_batch

    return sign_audit_flush_batch(
        events,
        watermark_before=watermark_before,
        watermark_after=watermark_after,
    )
