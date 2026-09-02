"""Production service URL resolution from environment."""

from __future__ import annotations

import os

SERVICE_DEFAULTS: dict[str, str] = {
    "registry": "http://127.0.0.1:8000",
    "coordinator": "http://127.0.0.1:8001",
    "aggregator": "http://127.0.0.1:8002",
}

SERVICE_ENV_KEYS: dict[str, str] = {
    "registry": "CFI_REGISTRY_URL",
    "coordinator": "CFI_COORDINATOR_URL",
    "aggregator": "CFI_AGGREGATOR_URL",
}

TLS_GATEWAY_ENV = "CFI_TLS_GATEWAY_URL"
TLS_GATEWAY_DEFAULT = "https://127.0.0.1:8443"


def resolve_service_url(service: str) -> str:
    """Resolve a federation service base URL from env or local default."""
    key = service.lower()
    if key not in SERVICE_DEFAULTS:
        raise ValueError(f"Unknown service: {service}. Choose from {sorted(SERVICE_DEFAULTS)}")
    env_key = SERVICE_ENV_KEYS[key]
    return os.getenv(env_key, SERVICE_DEFAULTS[key]).rstrip("/")


def federation_endpoints() -> dict[str, str]:
    """Return registry, coordinator, and aggregator URLs for smoke tests."""
    return {name: resolve_service_url(name) for name in SERVICE_DEFAULTS}


def default_registry_url() -> str:
    return resolve_service_url("registry")


def default_coordinator_url() -> str:
    return resolve_service_url("coordinator")


def default_aggregator_url() -> str:
    return resolve_service_url("aggregator")


def all_endpoint_env() -> dict[str, str]:
    """Federation and replay hook URLs resolved from environment."""
    from cfi_contributor.replay_profiles import REPLAY_PROFILES

    endpoints = federation_endpoints()
    hooks = {spec.endpoint_env: os.getenv(spec.endpoint_env, spec.default_url) for spec in REPLAY_PROFILES.values()}
    gateway = os.getenv(TLS_GATEWAY_ENV)
    if gateway:
        endpoints["tls_gateway"] = gateway.rstrip("/")
    return {**endpoints, **hooks}


def resolve_tls_gateway() -> str:
    return os.getenv(TLS_GATEWAY_ENV, TLS_GATEWAY_DEFAULT).rstrip("/")


def tls_federation_endpoints(gateway: str | None = None) -> dict[str, str]:
    """Federation service URLs behind nginx TLS gateway path prefixes."""
    base = (gateway or resolve_tls_gateway()).rstrip("/")
    return {
        "registry": f"{base}/registry",
        "coordinator": f"{base}/coordinator",
        "aggregator": f"{base}/aggregator",
    }


def tls_hook_env(gateway: str | None = None) -> dict[str, str]:
    """Replay hook URLs routed through nginx TLS gateway."""
    base = (gateway or resolve_tls_gateway()).rstrip("/")
    return {
        "CFI_REPLAY_MOCK_URL": f"{base}/replay/replay",
        "CFI_AGENTRX_URL": f"{base}/agentrx/v1/replay",
        "CFI_CAUSALFLOW_URL": f"{base}/causalflow/v1/counterfactual",
        "CFI_TAU_BENCH_URL": f"{base}/tau/v1/tasks",
    }


def apply_tls_hook_env(gateway: str | None = None) -> None:
    for key, value in tls_hook_env(gateway).items():
        os.environ[key] = value


def helm_federation_endpoints(
    host: str = "cfi-fed.local",
    *,
    tls: bool = True,
) -> dict[str, str]:
    """Federation URLs matching Helm ingress path prefixes (/registry, /coordinator, /aggregator)."""
    scheme = "https" if tls else "http"
    base = f"{scheme}://{host}"
    return {
        "registry": f"{base}/registry",
        "coordinator": f"{base}/coordinator",
        "aggregator": f"{base}/aggregator",
    }

