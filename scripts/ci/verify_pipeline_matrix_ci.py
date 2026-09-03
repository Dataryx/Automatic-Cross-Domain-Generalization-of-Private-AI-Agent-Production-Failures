#!/usr/bin/env python3
"""Run all pipeline smokes and require full pipeline matrix (CI)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STEPS = [
    "scripts/ci/verify_full_pipeline.py",
    "scripts/ci/verify_compose_full_pipeline.py",
    "scripts/ci/verify_postgres_compose_full_pipeline.py",
    "scripts/ci/verify_tls_full_pipeline.py",
    "scripts/ci/verify_mtls_full_pipeline.py",
    "scripts/ci/verify_postgres_tls_full_pipeline.py",
    "scripts/ci/verify_mtls_required_full_pipeline.py",
]


def main() -> int:
    if os.getenv("CFI_REQUIRE_DOCKER", "0") != "1":
        print("SKIP: CFI_REQUIRE_DOCKER not set", file=sys.stderr)
        return 0

    failed: list[str] = []
    for script in STEPS:
        print(f"\n=== {script} ===")
        result = subprocess.run([sys.executable, script], cwd=ROOT)
        if result.returncode != 0:
            failed.append(script)
    if failed:
        print(f"Pipeline CI failed: {', '.join(failed)}", file=sys.stderr)
        return 1

    os.environ["CFI_PIPELINE_REQUIRE_ALL"] = "1"
    matrix = subprocess.run([sys.executable, "scripts/ci/verify_pipeline_matrix.py"], cwd=ROOT)
    return matrix.returncode


if __name__ == "__main__":
    sys.exit(main())
