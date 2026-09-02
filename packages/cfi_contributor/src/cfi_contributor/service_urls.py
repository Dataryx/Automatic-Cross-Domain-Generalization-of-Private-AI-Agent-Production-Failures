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
