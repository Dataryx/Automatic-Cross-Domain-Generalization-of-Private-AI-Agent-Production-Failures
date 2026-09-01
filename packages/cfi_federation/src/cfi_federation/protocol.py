"""End-to-end protocol helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation import ClippedContribution, secure_aggregate, shamir_share
from cfi_federation.zk_attestation import prove_circuit_execution
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext
from cfi_recipient.sandbox import Sandbox, evaluate_case


def tenant_id_hash(tenant_id: str) -> str:
    return hashlib.sha256(tenant_id.encode()).hexdigest()


def build_share_envelope(
    tenant_id: str,
    epoch: str,
    failures: int,
    trials: int,
    clip_f: int,
    clip_n: int,
    threshold: int = 2,
    num_shares: int = 3,
) -> dict[str, Any]:
    clipped_f = min(failures, clip_f)
    clipped_n = min(trials, clip_n)
    return {
        "schema": "share-envelope/1.0",
        "tenant_id_hash": tenant_id_hash(tenant_id),
        "epoch": epoch,
        "shares_f": [list(s) for s in shamir_share(clipped_f, threshold, num_shares)],
        "shares_n": [list(s) for s in shamir_share(clipped_n, threshold, num_shares)],
        "coverage_share": 1.0,
        "measurement_spec_id": epoch,
    }


def recipient_evaluate_and_contribute(
    cfi_package: dict[str, Any],
    domain: str,
    tenant_id: str,
    manifest: CohortManifest,
    roles: list[str],
) -> tuple[ClippedContribution, dict[str, Any], int]:
    from cfi_core.models import CausalFailureInvariant

    cfi = CausalFailureInvariant.model_validate(cfi_package)
    mappings = [
        OntologyMapping(invariant_role=r, local_entity_id=f"local_{r}", status=MappingStatus.APPROVED)
        for r in roles
    ]
    ctx = RecipientContext(domain=domain, mappings=mappings)
    compilation = fail_closed_compile(cfi, ctx, manifest=manifest, seed=0)
    if compilation.abstained:
        raise ValueError(f"Compilation abstained: {compilation.abstention_reason}")

    def failing_agent(sb: Sandbox, trace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    failures = 0
    trials = 0
    positives = [c for c in compilation.cases if not c.is_negative_control]
    for case in positives:
        trials += 1
        ev = evaluate_case(case, cfi.oracle.expression, failing_agent)
        if ev.verdict.value == "fail":
            failures += 1

    contrib = ClippedContribution(
        tenant_id=tenant_id,
        failures=min(failures, manifest.clipping_f),
        trials=min(trials, manifest.clipping_n),
        coverage=1.0,
    )
    envelope = build_share_envelope(
        tenant_id,
        manifest.aggregation_epoch,
        contrib.failures,
        contrib.trials,
        manifest.clipping_f,
        manifest.clipping_n,
    )
    attestation = prove_circuit_execution(
        {"failures": contrib.failures, "trials": contrib.trials, "clip_f": manifest.clipping_f, "clip_n": manifest.clipping_n}
    )
    return contrib, envelope, failures


def run_federation_round(
    contributions: list[ClippedContribution],
    manifest: CohortManifest,
) -> dict[str, Any] | None:
    release = secure_aggregate(
        contributions,
        [],
        threshold=2,
        minimum_k=manifest.minimum_cohort_k,
        epsilon=manifest.privacy_budget_epsilon,
        measurement_spec_id=manifest.measurement_spec.spec_id,
    )
    if release is None:
        return None
    return {
        "released": True,
        "noisy_prevalence": release.noisy_prevalence,
        "epsilon": release.epsilon,
        "cohort_size": release.cohort_size,
        "assumptions": release.assumptions,
        "measurement_spec_id": release.measurement_spec_id,
    }
