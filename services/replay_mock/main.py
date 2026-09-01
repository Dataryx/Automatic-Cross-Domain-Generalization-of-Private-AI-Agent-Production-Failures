"""Minimal mock replay server for HttpAgentReplayProvider integration tests."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from cfi_core.middleware import configure_service_app
from cfi_core.observability import service_health
from cfi_core.tracing import configure_tracing, tracing_status

configure_tracing("replay_mock")

app = FastAPI(title="CFI Replay Mock")
configure_service_app(app, "replay_mock")


class ReplayRequest(BaseModel):
    nodes: dict
    edges: list
    seed: int = 0


@app.post("/replay")
@app.post("/v1/replay")
@app.post("/v1/counterfactual")
def replay(req: ReplayRequest) -> dict[str, float]:
    # Deterministic structural oracle: fail when policy_flow edges present without intervention
    has_intervention = any("intervention" in v for v in req.nodes.values())
    has_policy = any(e.get("relation") == "policy_flow" for e in req.edges)
    if has_intervention:
        return {"failure_rate": 0.0}
    return {"failure_rate": 1.0 if has_policy else 0.5}


@app.get("/tracing")
def tracing() -> dict[str, str | bool]:
    return tracing_status()


@app.get("/health")
def health() -> dict[str, str]:
    return service_health("replay_mock")


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CFI_HOST", "127.0.0.1"), port=int(os.getenv("CFI_PORT", "8010")))
