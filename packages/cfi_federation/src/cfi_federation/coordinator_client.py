"""HTTP client for cohort coordinator service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx


class _TestClientHttp:
    def __init__(self, test_client: object) -> None:
        self._test_client = test_client

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._test_client.post(path, json=kwargs.get("json"), headers=kwargs.get("headers"))  # type: ignore[attr-defined]

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._test_client.get(path, headers=kwargs.get("headers"))  # type: ignore[attr-defined]

    def close(self) -> None:
        return None


@dataclass
class CoordinatorClient:
    """Run consortium rounds against a remote coordinator."""

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
    def from_env(cls, base_url: str) -> CoordinatorClient:
        return cls(base_url=base_url)

    @classmethod
    def for_app(cls, app: object) -> CoordinatorClient:
        from fastapi.testclient import TestClient

        instance = cls("http://test")
        instance._client = _TestClientHttp(TestClient(app))
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
            )
            self._owns_client = True
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> CoordinatorClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        response = self._http().get("/health")
        response.raise_for_status()
        return response.json()

    def consortium_round(
        self,
        *,
        tenants: int = 12,
        seed: int = 421337,
        minimum_k: int = 10,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tenants": tenants,
            "seed": seed,
            "minimum_k": minimum_k,
        }
        if domains is not None:
            payload["domains"] = domains
        response = self._http().post("/consortium/round", json=payload)
        response.raise_for_status()
        return response.json()
