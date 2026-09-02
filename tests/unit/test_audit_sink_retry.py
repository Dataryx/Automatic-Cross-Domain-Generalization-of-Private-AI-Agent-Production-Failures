"""Audit sink webhook retry tests."""

from unittest.mock import MagicMock, patch

from cfi_governance.audit_sink import AuditSink


def test_webhook_retries_on_server_error() -> None:
    sink = AuditSink(webhook_url="http://example.test/audit", max_retries=3)
    response_fail = MagicMock(status_code=503)
    response_ok = MagicMock(status_code=202)
    with patch("httpx.post", side_effect=[response_fail, response_ok]) as post:
        with patch("cfi_governance.audit_sink.time.sleep"):
            result = sink.emit([{"action": "cfi.registered"}])
    assert result.webhook_status == 202
    assert result.webhook_attempts == 2
    assert post.call_count == 2


def test_webhook_does_not_retry_client_error() -> None:
    sink = AuditSink(webhook_url="http://example.test/audit", max_retries=3)
    response = MagicMock(status_code=400)
    with patch("httpx.post", return_value=response) as post:
        result = sink.emit([{"action": "cfi.registered"}])
    assert result.webhook_status == 400
    assert result.webhook_attempts == 1
    assert post.call_count == 1
