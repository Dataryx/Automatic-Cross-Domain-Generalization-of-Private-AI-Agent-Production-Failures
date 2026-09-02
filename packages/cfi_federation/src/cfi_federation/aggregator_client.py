"""HTTP client for remote aggregation service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from cfi_core.http_tls import httpx_client_options
from cfi_federation import ClippedContribution
from cfi_federation.zk_attestation import attestation_to_json


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
class AggregatorClient:
    """Submit clipped contributions to a running aggregation service."""

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
    def from_env(cls, base_url: str) -> AggregatorClient:
        return cls(base_url=base_url)

    @classmethod
    def for_app(cls, app: object) -> AggregatorClient:
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
                **httpx_client_options(),
            )
            self._owns_client = True
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> AggregatorClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def accountant(self) -> dict[str, Any]:
        response = self._http().get("/accountant")
        response.raise_for_status()
        return response.json()

    def aggregate(
        self,
        contributions: list[ClippedContribution],
        *,
        epsilon: float,
        minimum_k: int,
        measurement_spec_id: str,
        cohort_id: str = "default",
        attestation: object | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contributions": [c.__dict__ for c in contributions],
            "epsilon": epsilon,
            "minimum_k": minimum_k,
            "measurement_spec_id": measurement_spec_id,
            "cohort_id": cohort_id,
        }
        if attestation is not None:
            from cfi_federation.zk_attestation import CircuitAttestation

            if isinstance(attestation, CircuitAttestation):
                payload["attestation"] = attestation_to_json(attestation)
            elif isinstance(attestation, dict):
                payload["attestation"] = attestation
            else:
                raise TypeError("attestation must be CircuitAttestation or dict")
        response = self._http().post("/aggregate", json=payload)
        response.raise_for_status()
        return response.json()
