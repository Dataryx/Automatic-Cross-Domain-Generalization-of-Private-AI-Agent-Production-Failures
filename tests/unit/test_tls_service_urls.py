"""TLS gateway URL resolution tests."""

from cfi_contributor.service_urls import tls_federation_endpoints, tls_hook_env


def test_tls_federation_endpoints() -> None:
    endpoints = tls_federation_endpoints("https://gateway.test:8443")
    assert endpoints["registry"] == "https://gateway.test:8443/registry"
    assert endpoints["coordinator"] == "https://gateway.test:8443/coordinator"
    assert endpoints["aggregator"] == "https://gateway.test:8443/aggregator"


def test_tls_hook_env() -> None:
    hooks = tls_hook_env("https://gateway.test:8443")
    assert hooks["CFI_AGENTRX_URL"] == "https://gateway.test:8443/agentrx/v1/replay"
    assert hooks["CFI_CAUSALFLOW_URL"] == "https://gateway.test:8443/causalflow/v1/counterfactual"
