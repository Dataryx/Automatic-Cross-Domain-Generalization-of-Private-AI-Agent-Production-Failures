"""Tests for audit sink idempotency ledger."""

from pathlib import Path

from cfi_governance.audit_idempotency import AuditIdempotencyLedger, compute_audit_batch_id


def test_compute_audit_batch_id_stable() -> None:
    events = [{"action": "register", "resource_id": "CFI-1"}]
    first = compute_audit_batch_id(watermark_before=0, watermark_after=1, events=events)
    second = compute_audit_batch_id(watermark_before=0, watermark_after=1, events=events)
    assert first == second
    assert len(first) == 64


def test_idempotency_ledger_persists(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.txt"
    ledger = AuditIdempotencyLedger(persist_path=ledger_path)
    assert ledger.record("batch-a") is True
    assert ledger.record("batch-a") is False
    assert ledger.has("batch-a")

    reloaded = AuditIdempotencyLedger(persist_path=ledger_path)
    assert reloaded.has("batch-a")
