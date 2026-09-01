"""Deployable aggregation service — N independent servers."""

from fastapi import FastAPI
from pydantic import BaseModel

from cfi_federation import ClippedContribution, secure_aggregate

app = FastAPI(title="CFI Aggregation Server")


class AggregateRequest(BaseModel):
    contributions: list[ClippedContribution]
    epsilon: float
    minimum_k: int
    measurement_spec_id: str


@app.post("/aggregate")
def aggregate(req: AggregateRequest) -> dict:
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
    }
