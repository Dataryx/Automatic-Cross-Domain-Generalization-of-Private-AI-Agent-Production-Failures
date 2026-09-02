"""HTTP client for remote CFI registry operations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from cfi_core.http_tls import httpx_client_options


class _TestClientHttp:
    """Minimal httpx.Client surface over Starlette TestClient."""

    def __init__(self, test_client: object) -> None:
        self._test_client = test_client

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._test_client.get(path, headers=kwargs.get("headers"))  # type: ignore[attr-defined]

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._test_client.post(  # type: ignore[attr-defined]
            path,
            json=kwargs.get("json"),
            headers=kwargs.get("headers"),
        )

    def close(self) -> None:
        return None


@dataclass
class RegistryClient:
    """Thin client for contributor/recipient workflows against a running registry."""

    base_url: str
    token: str | None = None
    timeout: float = 30.0
    _client: httpx.Client | _TestClientHttp | None = field(default=None, repr=False)
    _owns_client: bool = field(default=True, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.token is None:
            self.token = os.getenv("CFI_API_TOKEN")

    @classmethod
    def from_env(cls, base_url: str) -> RegistryClient:
        return cls(base_url=base_url)

    @classmethod
    def for_app(cls, app: object) -> RegistryClient:
        """In-process client backed by FastAPI TestClient (tests/smoke only)."""
        from fastapi.testclient import TestClient

        instance = cls("http://test")
        instance._client = _TestClientHttp(TestClient(app))  # type: ignore[arg-type]
        instance._owns_client = False
        return instance

    def _headers(self) -> dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _http(self) -> httpx.Client | _TestClientHttp:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers(),
                **httpx_client_options(),
            )
            self._owns_client = True
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> RegistryClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        response = self._http().get("/health")
        response.raise_for_status()
        return response.json()

    def register(self, package: dict[str, Any]) -> dict[str, Any]:
        response = self._http().post("/cfi/register", json={"package": package})
        response.raise_for_status()
        return response.json()

    def get_cfi(self, invariant_id: str) -> dict[str, Any]:
        response = self._http().get(f"/cfi/{invariant_id}")
        response.raise_for_status()
        return response.json()

    def get_lifecycle(self, invariant_id: str) -> dict[str, Any]:
        response = self._http().get(f"/cfi/{invariant_id}/lifecycle")
        response.raise_for_status()
        return response.json()

    def audit_status(self) -> dict[str, Any]:
        response = self._http().get("/audit/status")
        response.raise_for_status()
        return response.json()

    def audit_export(self) -> dict[str, Any]:
        response = self._http().get("/audit/export")
        response.raise_for_status()
        return response.json()
