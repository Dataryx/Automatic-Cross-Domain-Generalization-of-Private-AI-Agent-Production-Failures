#!/usr/bin/env python3
"""Run all evaluation harnesses in sequence."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STEPS = [
    ("pytest", [sys.executable, "-m", "pytest", "tests/", "-q"]),
    ("verify_dod", [sys.executable, "tools/evaluation/verify_dod.py"]),
    ("health_check", [sys.executable, "scripts/ops/health_check.py"]),
    ("verify_sim", [sys.executable, "scripts/ci/verify_sim.py"]),
    ("verify_field_study", [sys.executable, "scripts/ci/verify_field_study.py"]),
    ("live_replay_smoke", [sys.executable, "scripts/ops/live_replay_smoke.py"]),
    ("verify_replay_profiles", [sys.executable, "scripts/ci/verify_replay_profiles.py"]),
    ("verify_corpus_ingest", [sys.executable, "scripts/ci/verify_corpus_ingest.py"]),
    ("verify_tls_stack", [sys.executable, "scripts/ci/verify_tls_stack.py"]),
    ("verify_observability", [sys.executable, "scripts/ci/verify_observability.py"]),
    ("verify_production_hardening", [sys.executable, "scripts/ci/verify_production_hardening.py"]),
    ("verify_auth", [sys.executable, "scripts/ci/verify_auth.py"]),
    ("verify_mtls", [sys.executable, "scripts/ci/verify_mtls.py"]),
    ("package_release", [sys.executable, "scripts/ops/package_release.py"]),
    ("verify_release", [sys.executable, "scripts/ci/verify_release.py"]),
    ("verify_eval_harnesses", [sys.executable, "scripts/ci/verify_eval_harnesses.py"]),
    ("verify_audit_attestation", [sys.executable, "scripts/ci/verify_audit_attestation.py"]),
    ("consortium_pilot", [sys.executable, "tools/evaluation/consortium/run_consortium_pilot.py"]),
    ("field_pilot", [sys.executable, "tools/evaluation/field/run_prospective_pilot.py"]),
    ("redteam", [sys.executable, "tools/evaluation/redteam/run_redteam.py"]),
    ("production_harness", [sys.executable, "tools/evaluation/production/harness.py"]),
    ("corpus_benchmark", [sys.executable, "tools/evaluation/benchmarks/run_corpus.py"]),
    ("tau_adapter", [sys.executable, "tools/evaluation/benchmarks/tau_adapter.py"]),
    ("golden_path", [sys.executable, "scripts/ops/golden_path.py"]),
    ("verify_full_pipeline", [sys.executable, "scripts/ci/verify_full_pipeline.py"]),
    ("cli_endpoints", [sys.executable, "scripts/ci/verify_cli_endpoints.py"]),
    ("pipeline_matrix", [sys.executable, "scripts/ci/verify_pipeline_matrix.py"]),
    ("compose_full_pipeline", [sys.executable, "scripts/ci/verify_compose_full_pipeline.py"]),
    ("postgres_compose_full_pipeline", [sys.executable, "scripts/ci/verify_postgres_compose_full_pipeline.py"]),
    ("tls_full_pipeline", [sys.executable, "scripts/ci/verify_tls_full_pipeline.py"]),
    ("mtls_full_pipeline", [sys.executable, "scripts/ci/verify_mtls_full_pipeline.py"]),
]


def main() -> int:
    failed: list[str] = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"\nFailed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll evaluation steps passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
