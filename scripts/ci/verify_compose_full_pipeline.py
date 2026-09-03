#!/usr/bin/env python3
"""Docker Compose full pipeline: publish -> assess -> federate -> consortium + agent hooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parents[1]
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))
import pathsetup

ROOT = pathsetup.ROOT
COMPOSE = ROOT / "docker-compose.yml"

from cfi_contributor.service_urls import federation_endpoints
from compose_docker import (
    compose_down,
    compose_logs,
    compose_up,
    docker_available,
    require_docker_enabled,
    wait_for_url,
)
from pipeline_smoke import run_remote_full_pipeline

CORE_CHECKS = [
    ("registry", "http://127.0.0.1:8000/health"),
    ("coordinator", "http://127.0.0.1:8001/health"),
    ("aggregator", "http://127.0.0.1:8002/health"),
]


def main() -> int:
    if not docker_available(require=require_docker_enabled()):
        return 0 if not require_docker_enabled() else 1
    if not COMPOSE.exists():
        print(f"Missing compose file: {COMPOSE}", file=sys.stderr)
        return 1

    print("Building and starting docker compose stack for full pipeline...")
    if compose_up(COMPOSE) != 0:
        return 1

    failed: list[str] = []
    try:
        for name, url in CORE_CHECKS:
            ok, message = wait_for_url(url)
            print(f"{name}: {message}")
            if not ok:
                failed.append(name)
        if failed:
            print(compose_logs(COMPOSE), file=sys.stderr)
            print(f"Compose health failed: {', '.join(failed)}", file=sys.stderr)
            return 1

        summary = run_remote_full_pipeline(
            federation_endpoints(),
            epoch="compose-full-pipeline",
            extra_assumptions=["Compose full pipeline uses docker-compose.yml services."],
        )
        out = ROOT / "tools/evaluation" / "output"
        out.mkdir(parents=True, exist_ok=True)
        (out / "compose_full_pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Compose full pipeline OK: {json.dumps(summary)}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        print(compose_logs(COMPOSE), file=sys.stderr)
        return 1
    finally:
        compose_down(COMPOSE)


if __name__ == "__main__":
    sys.exit(main())
