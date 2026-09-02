"""Service URL resolution tests."""

from cfi_contributor.service_urls import federation_endpoints, resolve_service_url


def test_resolve_service_url_defaults() -> None:
    assert resolve_service_url("registry") == "http://127.0.0.1:8000"
    assert resolve_service_url("coordinator") == "http://127.0.0.1:8001"
    assert resolve_service_url("aggregator") == "http://127.0.0.1:8002"


def test_resolve_service_url_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CFI_REGISTRY_URL", "http://registry.example:9000/")
    assert resolve_service_url("registry") == "http://registry.example:9000"


def test_federation_endpoints_keys() -> None:
    endpoints = federation_endpoints()
    assert set(endpoints) == {"registry", "coordinator", "aggregator"}
    for value in endpoints.values():
        assert value.startswith("http://")
