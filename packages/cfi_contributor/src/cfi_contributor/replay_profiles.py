"""Production replay profile resolution for AgentRx / CausalFlow hooks."""

from __future__ import annotations

import os
from dataclasses import dataclass

from cfi_contributor.replay import HttpAgentReplayProvider, ReplayProvider, StructuralReplayProvider


@dataclass(frozen=True)
class ReplayProfileSpec:
    name: str
    endpoint_env: str
    default_url: str
    notes: str

REPLAY_PROFILES: dict[str, ReplayProfileSpec] = {
    "mock": ReplayProfileSpec(
        name="mock",
        endpoint_env="CFI_REPLAY_MOCK_URL",
        default_url="http://127.0.0.1:8010/replay",
        notes="Local replay mock for integration tests; not a live agent.",
    ),
    "agentrx": ReplayProfileSpec(
        name="agentrx",
        endpoint_env="CFI_AGENTRX_URL",
        default_url="http://127.0.0.1:8020/v1/replay",
        notes="Sandboxed AgentRx diagnostic endpoint; causal identification not guaranteed.",
    ),
    "causalflow": ReplayProfileSpec(
        name="causalflow",
        endpoint_env="CFI_CAUSALFLOW_URL",
        default_url="http://127.0.0.1:8021/v1/counterfactual",
        notes="Sandboxed CausalFlow counterfactual endpoint; causal identification not guaranteed.",
    ),
}


LIVE_HOOK_ENV: dict[str, str] = {
    "agentrx": "CFI_AGENTRX_URL",
    "causalflow": "CFI_CAUSALFLOW_URL",
}


def list_profiles() -> list[str]:
    return sorted(REPLAY_PROFILES.keys())


def resolve_replay_provider(
    *,
    replay_url: str | None = None,
    replay_profile: str | None = None,
) -> ReplayProvider:
    """Resolve replay provider from explicit URL, named profile, or structural fallback."""
    if replay_url:
        return HttpAgentReplayProvider(replay_url)
    if replay_profile:
        key = replay_profile.lower()
        if key not in REPLAY_PROFILES:
            raise ValueError(f"Unknown replay profile: {replay_profile}. Choose from {list_profiles()}")
        spec = REPLAY_PROFILES[key]
        url = os.getenv(spec.endpoint_env, spec.default_url)
        return HttpAgentReplayProvider(url)
    return StructuralReplayProvider()


def profile_assumptions(replay_profile: str | None) -> list[str]:
    if not replay_profile:
        return ["Structural replay only; no live agent oracle."]
    spec = REPLAY_PROFILES.get(replay_profile.lower())
    if spec is None:
        return []
    return [spec.notes, f"Endpoint env: {spec.endpoint_env}"]
