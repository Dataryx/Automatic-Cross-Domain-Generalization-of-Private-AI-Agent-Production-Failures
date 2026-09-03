#!/usr/bin/env python3
"""TLS-terminated compose full pipeline via nginx gateway on :8443."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1]
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
import pathsetup

ROOT = pathsetup.ROOT
COMPOSE = ROOT / "docker-compose.tls.yml"
CERT_DIR = ROOT / "deploy" / "tls" / "certs"
CERT_GEN = ROOT / "scripts" / "ops" / "generate_dev_certs.py"

from cfi_contributor.service_urls import apply_tls_hook_env, tls_federation_endpoints
from compose_docker import (
    compose_down,
    compose_logs,
    compose_up,
    docker_available,
    require_docker_enabled,
    wait_for_url,
)
from pipeline_smoke import run_remote_full_pipeline

TLS_CHECKS = [
    ("nginx /health", "https://127.0.0.1:8443/health"),
    ("registry /health", "https://127.0.0.1:8443/registry/health"),
    ("coordinator /health", "https://127.0.0.1:8443/coordinator/health"),
    ("aggregator /health", "https://127.0.0.1:8443/aggregator/health"),
]


def _ensure_dev_certs() -> int:
    required = ("server.cert.pem", "server.key.pem")
    if all((CERT_DIR / name).exists() for name in required):
        return 0
    if not CERT_GEN.exists():
        print(f"Missing cert generator: {CERT_GEN}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(CERT_GEN)], cwd=ROOT)
    return result.returncode


def main() -> int:
    if not docker_available(require=require_docker_enabled()):
        return 0 if not require_docker_enabled() else 1
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1
    if _ensure_dev_certs() != 0:
        return 1

    print("Building and starting TLS compose stack for full pipeline...")
    if compose_up(COMPOSE) != 0:
        return 1

    failed: list[str] = []
    try:
        for label, url in TLS_CHECKS:
            ok, message = wait_for_url(url, verify=False)
            print(f"{label}: {message}")
            if not ok:
                failed.append(label)
        if failed:
            print(compose_logs(COMPOSE), file=sys.stderr)
            print(f"TLS compose health failed: {', '.join(failed)}", file=sys.stderr)
            return 1

        import os

        os.environ["CFI_TLS_VERIFY"] = "0"
        apply_tls_hook_env()
        endpoints = tls_federation_endpoints()
        summary = run_remote_full_pipeline(
            endpoints,
            epoch="tls-full-pipeline",
            extra_assumptions=[
                "TLS full pipeline uses nginx gateway with dev self-signed certificates.",
                "Set CFI_TLS_VERIFY=1 and CFI_TLS_CA_BUNDLE in production.",
            ],
        )
        summary["tls_gateway"] = endpoints["registry"].rsplit("/registry", 1)[0]
        out = ROOT / "tools/evaluation" / "output"
        out.mkdir(parents=True, exist_ok=True)
        (out / "tls_full_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"TLS full pipeline OK: {json.dumps(summary)}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print(compose_logs(COMPOSE), file=sys.stderr)
        return 1
    finally:
        compose_down(COMPOSE)


if __name__ == "__main__":
    sys.exit(main())
