"""Registry service and cohort coordinator — stores CFIs only, no raw traces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cfi_core.wire import CohortManifest
from cfi_governance import ArtifactRecord, LifecycleManager, LifecycleState


class RegisterRequest(BaseModel):
    package: dict[str, Any]


class CohortPublishRequest(BaseModel):
    manifest: CohortManifest


class LifecycleTransitionRequest(BaseModel):
    to_state: LifecycleState
    actor: str
    reason: str


class RegistryStoreProtocol(Protocol):
    def register(self, package: dict[str, Any]) -> str: ...
    def get(self, invariant_id: str) -> dict[str, Any]: ...
    def publish_cohort(self, manifest: CohortManifest) -> str: ...
    def get_lifecycle(self, invariant_id: str) -> ArtifactRecord: ...
    def transition_lifecycle(
        self, invariant_id: str, to_state: LifecycleState, actor: str, reason: str
    ) -> ArtifactRecord: ...


class RegistryStore:
    """In-memory store; production uses PostgreSQL append-only tables."""

    def __init__(self) -> None:
        self._cfis: dict[str, dict[str, Any]] = {}
        self._records: dict[str, ArtifactRecord] = {}
        self._manifests: dict[str, CohortManifest] = {}
        self._lifecycle = LifecycleManager()

    def register(self, package: dict[str, Any]) -> str:
        from cfi_registry.validation import validate_and_parse_package

        cfi = validate_and_parse_package(package)
        if cfi.id in self._cfis:
            raise ValueError("Duplicate invariant id")
        self._cfis[cfi.id] = package
        self._records[cfi.id] = ArtifactRecord(
            invariant_id=cfi.id,
            state=LifecycleState.REVIEWED,
            version="1.0.0",
        )
        return cfi.id

    def get(self, invariant_id: str) -> dict[str, Any]:
        if invariant_id not in self._cfis:
            raise KeyError(invariant_id)
        return self._cfis[invariant_id]

    def publish_cohort(self, manifest: CohortManifest) -> str:
        if manifest.invariant_id not in self._cfis:
            raise ValueError("Unknown invariant")
        if manifest.frozen:
            raise ValueError("Manifest already frozen")
        manifest = manifest.model_copy(update={"frozen": True})
        self._manifests[manifest.aggregation_epoch] = manifest
        return manifest.aggregation_epoch

    def get_lifecycle(self, invariant_id: str) -> ArtifactRecord:
        if invariant_id not in self._records:
            raise KeyError(invariant_id)
        return self._records[invariant_id]

    def transition_lifecycle(
        self, invariant_id: str, to_state: LifecycleState, actor: str, reason: str
    ) -> ArtifactRecord:
        record = self.get_lifecycle(invariant_id)
        ts = datetime.now(timezone.utc).isoformat()
        updated = self._lifecycle.transition(record, to_state, actor, reason, ts)
        self._records[invariant_id] = updated
        return updated


def create_app(store: RegistryStoreProtocol | None = None) -> FastAPI:
    app = FastAPI(title="CFI Registry", version="0.1.0")
    registry: RegistryStoreProtocol = store or RegistryStore()

    @app.post("/cfi/register")
    def register_cfi(req: RegisterRequest) -> dict[str, str]:
        try:
            iid = registry.register(req.package)
            return {"invariant_id": iid, "status": "registered"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/cfi/{invariant_id}")
    def get_cfi(invariant_id: str) -> dict[str, Any]:
        try:
            return registry.get(invariant_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    @app.get("/cfi/{invariant_id}/lifecycle")
    def get_lifecycle(invariant_id: str) -> dict[str, Any]:
        try:
            return registry.get_lifecycle(invariant_id).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    @app.post("/cfi/{invariant_id}/lifecycle")
    def transition_lifecycle(invariant_id: str, req: LifecycleTransitionRequest) -> dict[str, Any]:
        try:
            record = registry.transition_lifecycle(
                invariant_id, req.to_state, req.actor, req.reason
            )
            return record.model_dump(mode="json")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/cohort/publish")
    def publish_cohort(req: CohortPublishRequest) -> dict[str, str]:
        try:
            epoch = registry.publish_cohort(req.manifest)
            return {"epoch": epoch, "status": "published"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

    return app
