#!/usr/bin/env python3
"""Verify mTLS dev certificate bundle and nginx config."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT / "deploy" / "tls" / "certs"
GEN = ROOT / "scripts" / "generate_dev_certs.py"
NGINX = ROOT / "deploy" / "nginx" / "nginx-mtls.conf"
COMPOSE = ROOT / "docker-compose.mtls.yml"

REQUIRED = [
    "ca.cert.pem",
    "server.cert.pem",
    "server.key.pem",
    "client.cert.pem",
    "client.key.pem",
]


def main() -> int:
    if not NGINX.exists() or not COMPOSE.exists():
        print("Missing mTLS deployment files", file=sys.stderr)
        return 1
    if not all((CERT_DIR / name).exists() for name in REQUIRED):
        result = subprocess.run([sys.executable, str(GEN)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    missing = [name for name in REQUIRED if not (CERT_DIR / name).exists()]
    if missing:
        print(f"Missing certs: {missing}", file=sys.stderr)
        return 1
    text = NGINX.read_text(encoding="utf-8")
    if "ssl_client_certificate" not in text or "ssl_verify_client" not in text:
        print("nginx-mtls.conf missing client verification directives", file=sys.stderr)
        return 1
    for route in ("/agentrx/", "/causalflow/"):
        if route not in text:
            print(f"nginx-mtls.conf missing replay route: {route}", file=sys.stderr)
            return 1
    print("mTLS verification OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
