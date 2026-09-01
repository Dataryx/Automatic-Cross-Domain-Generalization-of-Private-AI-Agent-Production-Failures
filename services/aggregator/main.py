"""Deployable aggregation service with privacy accountant."""

import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cfi_federation import ClippedContribution, secure_aggregate
from cfi_federation.accountant import PrivacyAccountant
from cfi_federation.zk_attestation import CircuitAttestation, verify_circuit_attestation

app = FastAPI(title="CFI Aggregation Server")
_accountant = PrivacyAccountant(total_epsilon=float(os.getenv("CFI_TOTAL_EPSILON", "10.0")))


class AggregateRequest(BaseModel):
    contributions: list[ClippedContribution]
    epsilon: float
    minimum_k: int
    measurement_spec_id: str
    cohort_id: str = "default"
    attestation: CircuitAttestation | None = None


@app.post("/aggregate")
def aggregate(req: AggregateRequest) -> dict:
    if req.attestation and not verify_circuit_attestation(req.attestation):
        raise HTTPException(status_code=400, detail="Invalid ZK attestation")

    verdict = _accountant.request_release(
        req.epsilon, len(req.contributions), req.cohort_id, req.measurement_spec_id
    )
    if not verdict.allowed:
        return {"released": False, "reason": verdict.reason}

    release = secure_aggregate(
        req.contributions,
        [],
        threshold=2,
        minimum_k=req.minimum_k,
        epsilon=req.epsilon,
        measurement_spec_id=req.measurement_spec_id,
    )
    if release is None:
        return {"released": False, "reason": "below_threshold"}
    return {
        "released": True,
        "noisy_prevalence": release.noisy_prevalence,
        "assumptions": release.assumptions,
        "measurement_spec_id": release.measurement_spec_id,
        "remaining_epsilon": verdict.remaining_epsilon,
    }


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CFI_HOST", "0.0.0.0"), port=int(os.getenv("CFI_PORT", "8002")))
