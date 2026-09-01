"""Registry service and cohort coordinator — stores CFIs only, no raw traces."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from cfi_core.middleware import configure_service_app
from cfi_core.observability import format_prometheus, service_health

from cfi_core.wire import CohortManifest
from cfi_governance import ArtifactRecord, LifecycleManager, LifecycleState
from cfi_governance.review import ReviewQueue, ReviewStatus, ReviewTicket
from cfi_registry.review_ui import render_review_detail, render_review_ui, ticket_to_dict


class RegisterRequest(BaseModel):
    package: dict[str, Any]


class CohortPublishRequest(BaseModel):
    manifest: CohortManifest


class LifecycleTransitionRequest(BaseModel):
    to_state: LifecycleState
    actor: str
    reason: str


class ReviewDecisionRequest(BaseModel):
    status: ReviewStatus
    reviewer: str
    notes: str = ""
    checklist_complete: bool = True


class SupersessionRequest(BaseModel):
    successor_id: str
    actor: str
    reason: str = ""


class RegistryStoreProtocol(Protocol):
    def register(self, package: dict[str, Any]) -> str: ...
    def get(self, invariant_id: str) -> dict[str, Any]: ...
    def publish_cohort(self, manifest: CohortManifest) -> str: ...
    def get_lifecycle(self, invariant_id: str) -> ArtifactRecord: ...
    def transition_lifecycle(
        self, invariant_id: str, to_state: LifecycleState, actor: str, reason: str
    ) -> ArtifactRecord: ...
    def list_review_queue(self) -> list[ReviewTicket]: ...
    def get_review_ticket(self, invariant_id: str) -> ReviewTicket: ...
    def review_decision(self, invariant_id: str, req: ReviewDecisionRequest) -> ReviewTicket: ...
    def supersede(self, invariant_id: str, req: SupersessionRequest) -> ArtifactRecord: ...
    def stats(self) -> dict[str, int]: ...


class RegistryStore:
    """In-memory store; production uses PostgreSQL append-only tables."""

    def __init__(self) -> None:
        self._cfis: dict[str, dict[str, Any]] = {}
        self._records: dict[str, ArtifactRecord] = {}
        self._manifests: dict[str, CohortManifest] = {}
        self._lifecycle = LifecycleManager()
        self._review = ReviewQueue()

    def register(self, package: dict[str, Any]) -> str:
        from cfi_contributor.adversaries import ReleaseGateAdversaries
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
        scores = ReleaseGateAdversaries().score_cfi(cfi)
        self._review.enqueue(
            cfi.id,
            {
                "source_attribution": scores.source_attribution,
                "reconstruction": scores.reconstruction,
                "linkability": scores.linkability,
            },
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

    def list_review_queue(self) -> list[ReviewTicket]:
        return self._review.list_pending()

    def get_review_ticket(self, invariant_id: str) -> ReviewTicket:
        return self._review.get(invariant_id)

    def review_decision(self, invariant_id: str, req: ReviewDecisionRequest) -> ReviewTicket:
        ticket = self._review.decide(
            invariant_id,
            req.status,
            req.reviewer,
            req.notes,
            req.checklist_complete,
        )
        if req.status == ReviewStatus.APPROVED:
            self.transition_lifecycle(invariant_id, LifecycleState.ACTIVE, req.reviewer, req.notes)
        elif req.status == ReviewStatus.REJECTED:
            self.transition_lifecycle(invariant_id, LifecycleState.REVOKED, req.reviewer, req.notes)
        return ticket

    def supersede(self, invariant_id: str, req: SupersessionRequest) -> ArtifactRecord:
        if req.successor_id not in self._cfis:
            raise ValueError("Successor CFI not registered")
        record = self.get_lifecycle(invariant_id)
        ts = datetime.now(timezone.utc).isoformat()
        updated = self._lifecycle.supersede(record, req.successor_id, req.actor, ts)
        self._records[invariant_id] = updated
        return updated

    def stats(self) -> dict[str, int]:
        return {
            "registered_cfis": len(self._cfis),
            "pending_reviews": len(self.list_review_queue()),
            "active_cfis": sum(1 for r in self._records.values() if r.state == LifecycleState.ACTIVE),
            "cohort_manifests": len(self._manifests),
        }


def create_app(store: RegistryStoreProtocol | None = None) -> FastAPI:
    app = FastAPI(title="CFI Registry", version="0.1.0")
    configure_service_app(app, "registry")
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

    @app.post("/cfi/{invariant_id}/supersede")
    def supersede_cfi(invariant_id: str, req: SupersessionRequest) -> dict[str, Any]:
        try:
            record = registry.supersede(invariant_id, req)
            return record.model_dump(mode="json")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/health")
    def health() -> dict[str, str]:
        return service_health("registry")

    @app.get("/ready")
    def ready() -> dict[str, str]:
        return service_health("registry", ready=True)

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics() -> str:
        stats = registry.stats()
        return format_prometheus(
            {f"cfi_registry_{key}": float(value) for key, value in stats.items()},
            help_text={
                "cfi_registry_pending_reviews": "CFIs awaiting human review.",
                "cfi_registry_active_cfis": "CFIs in active lifecycle state.",
            },
        )

    @app.get("/cfi/{invariant_id}/audit")
    def audit_cfi(invariant_id: str) -> dict[str, Any]:
        try:
            ticket = registry.get_review_ticket(invariant_id)
            lifecycle = registry.get_lifecycle(invariant_id)
            return {
                "invariant_id": invariant_id,
                "lifecycle_state": lifecycle.state.value,
                "review_status": ticket.status.value,
                "adversary_scores": ticket.adversary_scores,
                "reviewer": ticket.reviewer,
                "assumptions": [
                    "Audit record reflects registration-time adversary scores.",
                    "Not a formal privacy audit.",
                ],
            }
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    @app.get("/review/queue")
    def review_queue() -> list[dict[str, Any]]:
        return [ticket_to_dict(t) for t in registry.list_review_queue()]

    @app.get("/review/ui", response_class=HTMLResponse)
    def review_ui() -> str:
        return render_review_ui(registry.list_review_queue())

    @app.get("/review/{invariant_id}")
    def review_ticket(invariant_id: str) -> dict[str, Any]:
        try:
            ticket = registry.get_review_ticket(invariant_id)
            lifecycle = registry.get_lifecycle(invariant_id)
            payload = ticket_to_dict(ticket)
            payload["lifecycle_state"] = lifecycle.state.value
            return payload
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    @app.get("/review/{invariant_id}/ui", response_class=HTMLResponse)
    def review_detail_ui(invariant_id: str) -> str:
        try:
            ticket = registry.get_review_ticket(invariant_id)
            lifecycle = registry.get_lifecycle(invariant_id)
            return render_review_detail(ticket, lifecycle.state.value)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

    @app.post("/review/{invariant_id}/decision")
    def review_decision(invariant_id: str, req: ReviewDecisionRequest) -> dict[str, Any]:
        try:
            ticket = registry.review_decision(invariant_id, req)
            return ticket_to_dict(ticket)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
