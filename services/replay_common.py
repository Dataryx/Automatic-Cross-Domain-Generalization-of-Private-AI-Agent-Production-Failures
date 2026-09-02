"""Shared replay stub logic for mock, AgentRx, and CausalFlow sandboxes."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from cfi_core.middleware import configure_service_app
from cfi_core.observability import service_health
from cfi_core.tracing import configure_tracing, tracing_status


class ReplayRequest(BaseModel):
    nodes: dict
    edges: list
    seed: int = 0


def compute_failure_rate(req: ReplayRequest) -> float:
    """Deterministic structural oracle; not a live agent."""
    has_intervention = any("intervention" in value for value in req.nodes.values())
    has_policy = any(edge.get("relation") == "policy_flow" for edge in req.edges)
    if has_intervention:
        return 0.0
    return 1.0 if has_policy else 0.5


def build_replay_response(profile: str, failure_rate: float, seed: int) -> dict[str, float | str]:
    response: dict[str, float | str] = {"failure_rate": failure_rate}
    if profile == "agentrx":
        response["diagnostic_id"] = f"arx-{seed}"
    elif profile == "causalflow":
        response["counterfactual_run_id"] = f"cf-{seed}"
    return response


def create_replay_app(service_name: str, profile: str) -> FastAPI:
    configure_tracing(service_name)
    app = FastAPI(title=f"CFI {service_name}")
    configure_service_app(app, service_name)

    @app.post("/replay")
    @app.post("/v1/replay")
    @app.post("/v1/counterfactual")
    def replay(req: ReplayRequest) -> dict[str, float | str]:
        rate = compute_failure_rate(req)
        return build_replay_response(profile, rate, req.seed)

    @app.get("/tracing")
    def tracing() -> dict[str, str | bool]:
        return tracing_status()

    @app.get("/health")
    def health() -> dict[str, str]:
        return service_health(service_name)

    return app


def run_replay_service(default_port: int, profile: str, service_name: str) -> None:
    app = create_replay_app(service_name, profile)
    uvicorn.run(
        app,
        host=os.getenv("CFI_HOST", "127.0.0.1"),
        port=int(os.getenv("CFI_PORT", str(default_port))),
    )
