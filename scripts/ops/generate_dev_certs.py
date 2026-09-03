#!/usr/bin/env python3
"""Generate dev TLS + mTLS certificate bundle for CFI-Fed."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[2]
CERT_DIR = ROOT / "deploy" / "tls" / "certs"


def _name(common_name: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CFI-Fed Dev"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )


def _write_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _write_cert(path: Path, cert: x509.Certificate) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def main() -> int:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=365)

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_subject = _name("CFI-Fed Dev CA")
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_subject = _name("cfi-fed.local")
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.DNSName("cfi-fed.local")]),
            critical=False,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_subject = _name("cfi-fed-client")
    client_cert = (
        x509.CertificateBuilder()
        .subject_name(client_subject)
        .issuer_name(ca_subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(expires)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    _write_cert(CERT_DIR / "ca.cert.pem", ca_cert)
    _write_key(CERT_DIR / "ca.key.pem", ca_key)
    _write_cert(CERT_DIR / "server.cert.pem", server_cert)
    _write_key(CERT_DIR / "server.key.pem", server_key)
    _write_cert(CERT_DIR / "client.cert.pem", client_cert)
    _write_key(CERT_DIR / "client.key.pem", client_key)

    print(f"Wrote TLS/mTLS bundle to {CERT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
