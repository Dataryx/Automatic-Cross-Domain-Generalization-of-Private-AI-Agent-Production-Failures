"""Minimal mock replay server for HttpAgentReplayProvider integration tests."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="CFI Replay Mock")


class ReplayRequest(BaseModel):
    nodes: dict
    edges: list
    seed: int = 0


@app.post("/replay")
def replay(req: ReplayRequest) -> dict[str, float]:
    # Deterministic structural oracle: fail when policy_flow edges present without intervention
    has_intervention = any("intervention" in v for v in req.nodes.values())
    has_policy = any(e.get("relation") == "policy_flow" for e in req.edges)
    if has_intervention:
        return {"failure_rate": 0.0}
    return {"failure_rate": 1.0 if has_policy else 0.5}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("CFI_HOST", "127.0.0.1"), port=int(os.getenv("CFI_PORT", "8010")))
