"""Deployable aggregation service with privacy accountant."""

import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from cfi_core.middleware import configure_service_app
from cfi_core.observability import format_prometheus, service_health
from cfi_core.tracing import configure_tracing, tracing_status
from cfi_federation import ClippedContribution, secure_aggregate
from cfi_federation.accountant import PrivacyAccountant
from cfi_federation.zk_attestation import CircuitAttestation, verify_circuit_attestation

configure_tracing("aggregator")

app = FastAPI(title="CFI Aggregation Server")
configure_service_app(app, "aggregator")
_accountant = PrivacyAccountant(total_epsilon=float(os.getenv("CFI_TOTAL_EPSILON", "10.0")))


class AggregateRequest(BaseModel):
    contributions: list[ClippedContribution]
    epsilon: float
    minimum_k: int
    measurement_spec_id: str
    cohort_id: str = "default"
    attestation: CircuitAttestation | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return service_health("aggregator")


@app.get("/ready")
def ready() -> dict[str, str]:
    return service_health("aggregator", ready=True)


@app.get("/accountant")
def accountant_status() -> dict[str, float | int]:
    return _accountant.snapshot()


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    snap = _accountant.snapshot()
    return format_prometheus(
        {
            "cfi_total_epsilon": float(snap["total_epsilon"]),
            "cfi_spent_epsilon": float(snap["spent_epsilon"]),
            "cfi_remaining_epsilon": float(snap["remaining_epsilon"]),
            "cfi_release_count": float(snap["release_count"]),
        },
        help_text={
            "cfi_remaining_epsilon": "Remaining differential privacy budget (epsilon).",
            "cfi_spent_epsilon": "Spent differential privacy budget (epsilon).",
        },
    )


@app.get("/tracing")
def tracing() -> dict[str, str | bool]:
    return tracing_status()


@app.post("/aggregate")
def aggregate(req: AggregateRequest) -> dict[str, Any]:
    if req.attestation and not verify_circuit_attestation(req.attestation):
        raise HTTPException(status_code=400, detail="Invalid ZK attestation")

    verdict = _accountant.request_release(
        req.epsilon, len(req.contributions), req.cohort_id, req.measurement_spec_id
    )
    if not verdict.allowed:
        return {"released": False, "reason": verdict.reason, "remaining_epsilon": verdict.remaining_epsilon}

    release = secure_aggregate(
        req.contributions,
        [],
        threshold=2,
        minimum_k=req.minimum_k,
        epsilon=req.epsilon,
        measurement_spec_id=req.measurement_spec_id,
    )
    if release is None:
        return {"released": False, "reason": "below_threshold", "remaining_epsilon": verdict.remaining_epsilon}
    return {
        "released": True,
        "noisy_prevalence": release.noisy_prevalence,
        "assumptions": release.assumptions,
        "measurement_spec_id": release.measurement_spec_id,
        "remaining_epsilon": verdict.remaining_epsilon,
    }


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CFI_HOST", "0.0.0.0"), port=int(os.getenv("CFI_PORT", "8002")))
