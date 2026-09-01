"""Deployable cohort coordinator — separate keys and DB from registry."""

from fastapi import FastAPI
from pydantic import BaseModel

from cfi_core.wire import CohortManifest

app = FastAPI(title="CFI Cohort Coordinator")


class PublishRequest(BaseModel):
    manifest: CohortManifest


@app.post("/epoch/open")
def open_epoch(req: PublishRequest) -> dict[str, str]:
    m = req.manifest.model_copy(update={"frozen": True})
    return {"epoch": m.aggregation_epoch, "status": "frozen", "invariant_id": m.invariant_id}
