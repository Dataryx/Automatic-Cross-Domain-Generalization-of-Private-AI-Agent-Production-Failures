"""TLS verify helper tests."""

from cfi_core.http_tls import httpx_client_cert, httpx_verify


def test_httpx_verify_default(monkeypatch) -> None:
    monkeypatch.delenv("CFI_TLS_VERIFY", raising=False)
    monkeypatch.delenv("CFI_TLS_CA_BUNDLE", raising=False)
    assert httpx_verify() is True


def test_httpx_verify_disabled(monkeypatch) -> None:
    monkeypatch.setenv("CFI_TLS_VERIFY", "0")
    assert httpx_verify() is False


def test_httpx_verify_ca_bundle(monkeypatch) -> None:
    monkeypatch.setenv("CFI_TLS_CA_BUNDLE", "/etc/ssl/certs/ca.pem")
    assert httpx_verify() == "/etc/ssl/certs/ca.pem"


def test_httpx_client_cert_from_env(monkeypatch) -> None:
    monkeypatch.setenv("CFI_MTLS_CLIENT_CERT", "/certs/client.pem")
    monkeypatch.setenv("CFI_MTLS_CLIENT_KEY", "/certs/client.key")
    assert httpx_client_cert() == ("/certs/client.pem", "/certs/client.key")


def test_httpx_client_options_includes_cert(monkeypatch) -> None:
    from cfi_core.http_tls import httpx_client_cert, httpx_client_options

    monkeypatch.setenv("CFI_MTLS_CLIENT_CERT", "/certs/client.pem")
    monkeypatch.setenv("CFI_MTLS_CLIENT_KEY", "/certs/client.key")
    opts = httpx_client_options()
    assert opts["cert"] == httpx_client_cert()
