"""HTTP middleware tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cfi_core.middleware import (
    REQUEST_ID_HEADER,
    RateLimitMiddleware,
    configure_service_app,
)
from cfi_registry import RegistryStore, create_app


def test_request_id_header_echoed() -> None:
    client = TestClient(create_app(RegistryStore()))
    resp = client.get("/health", headers={REQUEST_ID_HEADER: "trace-abc"})
    assert resp.status_code == 200
    assert resp.headers[REQUEST_ID_HEADER] == "trace-abc"


def test_request_id_generated_when_missing() -> None:
    client = TestClient(create_app(RegistryStore()))
    resp = client.get("/health")
    assert resp.status_code == 200
    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) >= 8


def test_rate_limit_blocks_excess_requests() -> None:
    app = FastAPI()

    @app.get("/work")
    def work() -> dict[str, str]:
        return {"ok": "true"}

    app.add_middleware(RateLimitMiddleware, max_requests=2, window_seconds=60)
    client = TestClient(app)
    assert client.get("/work").status_code == 200
    assert client.get("/work").status_code == 200
    blocked = client.get("/work")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "rate_limit_exceeded"


def test_health_endpoints_bypass_rate_limit() -> None:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60)
    client = TestClient(app)
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_configure_service_app_adds_request_context() -> None:
    app = FastAPI()
    configure_service_app(app, "test-service")

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"pong": "1"}

    client = TestClient(app)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert REQUEST_ID_HEADER in resp.headers
