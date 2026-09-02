"""Production agent hook probes for replay profiles (sandbox diagnostics only)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

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


def resolve_profile_replay_url(profile: str) -> str:
    """Resolve replay endpoint URL from env or profile default."""
    key = profile.lower()
    if key not in REPLAY_PROFILES:
        raise ValueError(f"Unknown replay profile: {profile}. Choose from {list_profiles()}")
    spec = REPLAY_PROFILES[key]
    return os.getenv(spec.endpoint_env, spec.default_url)


def resolve_profile_health_base(profile: str) -> str:
    """Resolve service base URL for /health probes from replay endpoint env."""
    parsed = urlparse(resolve_profile_replay_url(profile))
    return f"{parsed.scheme}://{parsed.netloc}"


def probe_replay_profile(
    profile: str,
    *,
    health_client: _HttpGetClient,
    replay_client: _HttpPostClient,
    path: str | None = None,
    replay_url: str | None = None,
) -> HookProbeResult:
    """Probe /health and replay endpoint for a named profile."""
    key = profile.lower()
    if key not in REPLAY_PROFILES:
        raise ValueError(f"Unknown replay profile: {profile}. Choose from {list_profiles()}")
    spec = REPLAY_PROFILES[key]
    route = path or PROFILE_PATHS[key]
    health = health_client.get("/health")
    healthy = getattr(health, "status_code", 0) == 200
    endpoint = replay_url or resolve_profile_replay_url(key)
    provider = HttpAgentReplayProvider(endpoint, client=replay_client)
    evidence = provider.estimate_failure_rate(IncidentGraph(), trials=2, seed=421337)
    replay_ok = 0.0 <= evidence.failure_rate <= 1.0
    return HookProbeResult(
        profile=key,
        healthy=healthy,
        replay_ok=replay_ok,
        failure_rate=evidence.failure_rate,
        notes=spec.notes,
    )


class _HttpxHealthClient:
    def __init__(self, base_url: str, client: object) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    def get(self, path: str) -> object:
        return self._client.get(f"{self._base_url}{path}")  # type: ignore[attr-defined]


class _HttpxReplayClient:
    def __init__(self, client: object) -> None:
        self._client = client

    def post(self, url: str, json: dict | None = None, timeout: float = 30.0) -> object:
        return self._client.post(url, json=json, timeout=timeout)  # type: ignore[attr-defined]


def probe_profile_http(profile: str) -> HookProbeResult:
    """Probe one replay profile against env-configured HTTP endpoints."""
    import httpx

    key = profile.lower()
    with httpx.Client(timeout=30.0) as client:
        return probe_replay_profile(
            key,
            health_client=_HttpxHealthClient(resolve_profile_health_base(key), client),
            replay_client=_HttpxReplayClient(client),
            replay_url=resolve_profile_replay_url(key),
        )


def probe_all_profiles_http() -> list[HookProbeResult]:
    """Probe all replay profiles against env-configured HTTP endpoints."""
    import httpx

    results: list[HookProbeResult] = []
    with httpx.Client(timeout=30.0) as client:
        for profile in list_profiles():
            base = resolve_profile_health_base(profile)
            replay_url = resolve_profile_replay_url(profile)
            results.append(
                probe_replay_profile(
                    profile,
                    health_client=_HttpxHealthClient(base, client),
                    replay_client=_HttpxReplayClient(client),
                    replay_url=replay_url,
                )
            )
    return results
