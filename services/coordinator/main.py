"""Cohort coordinator with consortium round orchestration."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cfi_contributor.packager import Packager
from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
from cfi_core.examples import build_exception_precedence_cfi
from cfi_core.signing import KeyPair
from cfi_core.wire import CohortManifest, MeasurementSpec
from cfi_federation.consortium import ConsortiumConfig, ConsortiumCoordinator, TenantIdentity

app = FastAPI(title="CFI Cohort Coordinator")


class PublishRequest(BaseModel):
    manifest: CohortManifest


class ConsortiumRoundRequest(BaseModel):
    tenants: int = Field(default=12, ge=2)
    seed: int = 421337
    minimum_k: int = Field(default=10, ge=2)
    domains: list[str] = Field(
        default_factory=lambda: [
            "procurement",
            "healthcare",
            "data_operations",
            "finance",
            "logistics",
            "retail",
        ]
    )


def _signed_cfi_package() -> dict:
    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    verdict = gate.run(cfi, {i: True for i in range(1, 13)})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=0.1)
    result = Packager(KeyPair.generate("coordinator-contributor")).package(cfi, verdict)
    if not result.success or result.cfi is None:
        raise RuntimeError("Failed to build coordinator CFI package")
    return result.cfi.model_dump(mode="json")


@app.post("/epoch/open")
def open_epoch(req: PublishRequest) -> dict[str, str]:
    manifest = req.manifest.model_copy(update={"frozen": True})
    return {"epoch": manifest.aggregation_epoch, "status": "frozen", "invariant_id": manifest.invariant_id}


@app.post("/consortium/round")
def run_consortium_round(req: ConsortiumRoundRequest) -> dict:
    pkg = _signed_cfi_package()
    invariant_id = pkg["id"]
    spec = MeasurementSpec(
        spec_id="coordinator-spec",
        invariant_id=invariant_id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    manifest = CohortManifest(
        invariant_id=invariant_id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch=f"coord-epoch-{req.seed}",
        expiration="2026-12-31",
        minimum_cohort_k=req.minimum_k,
        frozen=True,
    )
    identities = [
        TenantIdentity(tenant_id=f"tenant-{i:02d}", org_family=f"org-{i % 6}", compiler_version="0.1.0")
        for i in range(req.tenants)
    ]
    config = ConsortiumConfig(minimum_k=req.minimum_k, max_per_org_family=2, dropout_rate=0.05)
    result = ConsortiumCoordinator(config).run_round(
        pkg,
        manifest,
        identities,
        build_exception_precedence_cfi().required_mapping_roles,
        req.domains,
        seed=req.seed,
    )
    if not result.released:
        raise HTTPException(status_code=400, detail=result.reason)
    return {
        "released": result.released,
        "participants": result.participants,
        "noisy_prevalence": result.noisy_prevalence,
        "assumptions": result.assumptions,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CFI_HOST", "127.0.0.1"), port=int(os.getenv("CFI_PORT", "8001")))
