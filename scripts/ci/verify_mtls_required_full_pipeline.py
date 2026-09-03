#!/usr/bin/env python3
"""mTLS required-mode compose full pipeline (client cert mandatory)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1]
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
import pathsetup

ROOT = pathsetup.ROOT
COMPOSE = ROOT / "docker-compose.mtls-required.yml"
CERT_DIR = ROOT / "deploy" / "tls" / "certs"
CERT_GEN = ROOT / "scripts" / "ops" / "generate_dev_certs.py"

from cfi_contributor.service_urls import apply_tls_hook_env, tls_federation_endpoints
from cfi_core.http_tls import apply_dev_mtls_client_env
from compose_docker import (
    compose_down,
    compose_logs,
    compose_up,
    docker_available,
    require_docker_enabled,
    wait_for_url,
)
from pipeline_smoke import run_remote_full_pipeline

CHECKS = [
    ("nginx /health", "https://127.0.0.1:8443/health"),
    ("registry /health", "https://127.0.0.1:8443/registry/health"),
]


def _ensure_dev_mtls_certs() -> int:
    required = ("server.cert.pem", "server.key.pem", "client.cert.pem", "client.key.pem", "ca.cert.pem")
    if all((CERT_DIR / name).exists() for name in required):
        return 0
    return subprocess.run([sys.executable, str(CERT_GEN)], cwd=ROOT).returncode


def main() -> int:
    if not docker_available(require=require_docker_enabled()):
        return 0 if not require_docker_enabled() else 1
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1
    if _ensure_dev_mtls_certs() != 0:
        return 1

    print("Building and starting mTLS-required compose stack...")
    if compose_up(COMPOSE) != 0:
        return 1

    try:
        os.environ["CFI_TLS_VERIFY"] = "0"
        apply_dev_mtls_client_env(CERT_DIR)
        apply_tls_hook_env()

        unauthenticated_ok, unauth_msg = wait_for_url(
            "https://127.0.0.1:8443/registry/health",
            verify=False,
            use_client_cert=False,
        )
        if unauthenticated_ok:
            print("Expected registry /health to reject connections without client cert", file=sys.stderr)
            return 1
        print(f"unauthenticated blocked: {unauth_msg}")

        failed = []
        for label, url in CHECKS:
            ok, message = wait_for_url(url, verify=False)
            print(f"{label}: {message}")
            if not ok:
                failed.append(label)
        if failed:
            print(compose_logs(COMPOSE), file=sys.stderr)
            return 1

        summary = run_remote_full_pipeline(
            tls_federation_endpoints(),
            epoch="mtls-required-full-pipeline",
            extra_assumptions=["nginx ssl_verify_client is on; client certificate is mandatory."],
        )
        out = ROOT / "tools/evaluation" / "output"
        out.mkdir(parents=True, exist_ok=True)
        (out / "mtls_required_full_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"mTLS-required full pipeline OK: {json.dumps(summary)}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print(compose_logs(COMPOSE), file=sys.stderr)
        return 1
    finally:
        compose_down(COMPOSE)


if __name__ == "__main__":
    sys.exit(main())
