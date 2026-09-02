#!/usr/bin/env python3
"""Verify TLS production stack artifacts (dev self-signed)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.tls.yml"
NGINX = ROOT / "deploy" / "nginx" / "nginx.conf"
CERT_DIR = ROOT / "deploy" / "tls" / "certs"
GEN = ROOT / "scripts" / "generate_dev_certs.py"


def main() -> int:
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1
    if not NGINX.exists():
        print(f"Missing nginx config: {NGINX}", file=sys.stderr)
        return 1
    text = NGINX.read_text(encoding="utf-8")
    if "ssl_certificate" not in text or "TLSv1.2" not in text:
        print("nginx.conf missing TLS directives", file=sys.stderr)
        return 1
    for route in ("/agentrx/", "/causalflow/", "/tau/"):
        if route not in text:
            print(f"nginx.conf missing replay route: {route}", file=sys.stderr)
            return 1

    if not (CERT_DIR / "server.cert.pem").exists():
        result = subprocess.run([sys.executable, str(GEN)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode

    if not (CERT_DIR / "server.key.pem").exists() or not (CERT_DIR / "server.cert.pem").exists():
        print("TLS certificates not generated", file=sys.stderr)
        return 1

    print("TLS stack verification OK (dev certs + nginx + compose)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
