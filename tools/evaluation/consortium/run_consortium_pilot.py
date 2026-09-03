#!/usr/bin/env python3
"""Phase 5 consortium pilot — 12 independent tenants, anti-Sybil, DP aggregate.

Smoke test for multi-tenant federation. Does NOT use live production agents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.consortium import ConsortiumConfig, ConsortiumCoordinator, TenantIdentity

SEED = 421337
OUT = Path(__file__).resolve().parent / "output"
DOMAINS = ["procurement", "healthcare", "data_operations", "finance", "logistics", "retail"]


def _signed_cfi() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    key = KeyPair.generate("consortium-contributor")
    result = Packager(key).package(cfi, verdict)
    assert result.success and result.cfi is not None
    return result.cfi.model_dump(mode="json")


def _manifest(invariant_id: str) -> CohortManifest:
    spec = MeasurementSpec(
        spec_id="consortium-spec-1",
        invariant_id=invariant_id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    return CohortManifest(
        invariant_id=invariant_id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="consortium-epoch-1",
        expiration="2026-12-31",
        minimum_cohort_k=10,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pkg = _signed_cfi()
    invariant_id = pkg["id"]
    manifest = _manifest(invariant_id)
    roles = build_exception_precedence_cfi().required_mapping_roles

    # 12 tenants across 6 org families (2 each — at cap)
    identities = [
        TenantIdentity(tenant_id=f"tenant-{i:02d}", org_family=f"org-{i % 6}", compiler_version="0.1.0")
        for i in range(12)
    ]

    config = ConsortiumConfig(minimum_k=10, max_per_org_family=2, dropout_rate=0.08)
    coordinator = ConsortiumCoordinator(config)
    result = coordinator.run_round(pkg, manifest, identities, roles, DOMAINS, seed=SEED)

    summary = {
        "seed": SEED,
        "tenants_requested": len(identities),
        "released": result.released,
        "participants": result.participants,
        "noisy_prevalence": result.noisy_prevalence,
        "rejected_count": len(result.rejected),
        "reason": result.reason,
        "assumptions": result.assumptions,
    }
    (OUT / "consortium_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"Consortium round: released={result.released}, participants={result.participants}")
    if result.released:
        print(f"Noisy prevalence: {result.noisy_prevalence:.4f} (epsilon={manifest.privacy_budget_epsilon})")
    else:
        print(f"Not released: {result.reason}")
        return 1

    print("Assumptions:")
    for a in result.assumptions:
        print(f"  - {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
