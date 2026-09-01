"""Governance audit log tests."""

from cfi_governance.audit_log import AuditLog


def test_audit_log_append_only() -> None:
    log = AuditLog()
    log.append("alice@org", "review.decision", "CFI-1", {"status": "approved"})
    log.append("system", "cfi.registered", "CFI-1")
    exported = log.export()
    assert len(exported) == 2
    assert exported[0]["action"] == "review.decision"
    assert exported[1]["actor"] == "system"
