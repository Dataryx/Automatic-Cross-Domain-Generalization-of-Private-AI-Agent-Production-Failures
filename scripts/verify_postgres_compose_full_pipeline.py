#!/usr/bin/env python3
"""Postgres compose full pipeline: publish -> assess -> federate -> consortium + agent hooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.postgres.yml"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfi_contributor.service_urls import federation_endpoints
from eval.compose_docker import (
    compose_down,
    compose_logs,
    compose_up,
    docker_available,
    require_docker_enabled,
    wait_for_url,
)
from eval.pipeline_smoke import run_remote_full_pipeline

REGISTRY_CHECKS = [
    ("registry /ready", "http://127.0.0.1:8000/ready"),
    ("coordinator /health", "http://127.0.0.1:8001/health"),
    ("aggregator /health", "http://127.0.0.1:8002/health"),
]


def main() -> int:
    if not docker_available(require=require_docker_enabled()):
        return 0 if not require_docker_enabled() else 1
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1

    print("Building and starting Postgres compose stack for full pipeline...")
    if compose_up(COMPOSE) != 0:
        return 1

    failed: list[str] = []
    try:
        for label, url in REGISTRY_CHECKS:
            ok, message = wait_for_url(url, timeout_s=180.0, interval_s=3.0)
            print(f"{label}: {message}")
            if not ok:
                failed.append(label)

        if not failed:
            import httpx

            status = httpx.get("http://127.0.0.1:8000/audit/status", timeout=10.0)
            if status.status_code != 200:
                failed.append("audit_status")
            else:
                print(f"audit/status OK: {status.json().get('event_count', 0)} events")

        if failed:
            print(compose_logs(COMPOSE), file=sys.stderr)
            print(f"Postgres compose health failed: {', '.join(failed)}", file=sys.stderr)
            return 1

        summary = run_remote_full_pipeline(
            federation_endpoints(),
            epoch="postgres-compose-full-pipeline",
            extra_assumptions=["Registry persistence uses PostgreSQL in this smoke."],
        )
        out = ROOT / "eval" / "output"
        out.mkdir(parents=True, exist_ok=True)
        (out / "postgres_compose_full_pipeline_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        print(f"Postgres compose full pipeline OK: {json.dumps(summary)}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print(compose_logs(COMPOSE), file=sys.stderr)
        return 1
    finally:
        compose_down(COMPOSE)


if __name__ == "__main__":
    sys.exit(main())
