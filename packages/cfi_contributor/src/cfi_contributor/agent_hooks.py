"""Production agent hook probes for replay profiles (sandbox diagnostics only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cfi_contributor.graph import IncidentGraph
from cfi_contributor.replay import HttpAgentReplayProvider
from cfi_contributor.replay_profiles import REPLAY_PROFILES, list_profiles


class _HttpGetClient(Protocol):
    def get(self, path: str) -> object: ...


class _HttpPostClient(Protocol):
    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object: ...


@dataclass
class HookProbeResult:
    profile: str
    healthy: bool
    replay_ok: bool
    failure_rate: float | None = None
    notes: str = ""


PROFILE_PATHS: dict[str, str] = {
    "mock": "/replay",
    "agentrx": "/v1/replay",
    "causalflow": "/v1/counterfactual",
}


def probe_replay_profile(
    profile: str,
    *,
    health_client: _HttpGetClient,
    replay_client: _HttpPostClient,
    path: str | None = None,
) -> HookProbeResult:
    """Probe /health and replay endpoint for a named profile."""
    key = profile.lower()
    if key not in REPLAY_PROFILES:
        raise ValueError(f"Unknown replay profile: {profile}. Choose from {list_profiles()}")
    spec = REPLAY_PROFILES[key]
    route = path or PROFILE_PATHS[key]
    health = health_client.get("/health")
    healthy = getattr(health, "status_code", 0) == 200
    provider = HttpAgentReplayProvider(spec.default_url, client=replay_client)
    evidence = provider.estimate_failure_rate(IncidentGraph(), trials=2, seed=421337)
    replay_ok = 0.0 <= evidence.failure_rate <= 1.0
    return HookProbeResult(
        profile=key,
        healthy=healthy,
        replay_ok=replay_ok,
        failure_rate=evidence.failure_rate,
        notes=spec.notes,
    )
