"""TLS / HTTP client settings shared across federation clients."""

from __future__ import annotations

import os
from typing import Any


def httpx_verify() -> bool | str:
    """Return httpx verify= value from CFI_TLS_VERIFY and optional CFI_TLS_CA_BUNDLE."""
    if os.getenv("CFI_TLS_VERIFY", "1").lower() in ("0", "false", "no"):
        return False
    ca_bundle = os.getenv("CFI_TLS_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle
    return True


def httpx_client_cert() -> tuple[str, str] | None:
    """Return client cert tuple when CFI_MTLS_CLIENT_CERT and CFI_MTLS_CLIENT_KEY are set."""
    cert = os.getenv("CFI_MTLS_CLIENT_CERT")
    key = os.getenv("CFI_MTLS_CLIENT_KEY")
    if cert and key:
        return (cert, key)
    return None


def httpx_client_options() -> dict[str, Any]:
    """Shared httpx.Client keyword arguments for federation HTTP clients."""
    options: dict[str, Any] = {"verify": httpx_verify()}
    cert = httpx_client_cert()
    if cert is not None:
        options["cert"] = cert
    return options


def apply_dev_mtls_client_env(cert_dir: str | os.PathLike[str]) -> None:
    """Point mTLS client env vars at dev certificate bundle paths."""
    base = os.fspath(cert_dir)
    os.environ["CFI_MTLS_CLIENT_CERT"] = os.path.join(base, "client.cert.pem")
    os.environ["CFI_MTLS_CLIENT_KEY"] = os.path.join(base, "client.key.pem")
