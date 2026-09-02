"""PostgreSQL append-only persistence for registry and lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from cfi_core.wire import CohortManifest
from cfi_governance import ArtifactRecord, LifecycleManager, LifecycleState
from cfi_governance.audit_sink import AuditSink, flush_audit_events
from cfi_governance.audit_watermark import AuditWatermark
from cfi_governance.review import ReviewStatus, ReviewTicket


class Base(DeclarativeBase):
    pass


class CFIRecord(Base):
    __tablename__ = "cfi_records"

    invariant_id: Mapped[str] = mapped_column(String, primary_key=True)
    package_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, default="cfi/1.0")
    signature: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ArtifactLifecycleRecord(Base):
    __tablename__ = "artifact_lifecycle"

    invariant_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReviewTicketRecord(Base):
    __tablename__ = "review_tickets"

    invariant_id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    adversary_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    checklist_complete: Mapped[bool] = mapped_column(default=False)
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class LifecycleHistory(Base):
    __tablename__ = "lifecycle_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invariant_id: Mapped[str] = mapped_column(String, index=True)
    from_state: Mapped[str] = mapped_column(String)
    to_state: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime)


class SupersessionChain(Base):
    __tablename__ = "supersession_chain"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invariant_id: Mapped[str] = mapped_column(String, index=True)
    successor_id: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime)


class CohortManifestRecord(Base):
    __tablename__ = "cohort_manifests"

    aggregation_epoch: Mapped[str] = mapped_column(String, primary_key=True)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    frozen: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostgresRegistryStore:
    """Append-only registry backing store."""

    def __init__(self, database_url: str, audit_sink: AuditSink | None = None, watermark: AuditWatermark | None = None) -> None:
        self._engine = create_engine(database_url, future=True)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._lifecycle = LifecycleManager()
        self._audit_sink = audit_sink if audit_sink is not None else AuditSink.from_env()
        self._watermark = watermark if watermark is not None else AuditWatermark.from_env()

    def _session(self) -> Session:
        return self._session_factory()

    def close(self) -> None:
        self._engine.dispose()

    def _save_artifact_record(self, record: ArtifactRecord) -> None:
        with self._session() as session:
            row = session.get(ArtifactLifecycleRecord, record.invariant_id)
            payload = record.model_dump_json()
            if row is None:
                session.add(
                    ArtifactLifecycleRecord(
                        invariant_id=record.invariant_id,
                        state=record.state.value,
                        version=record.version,
                        record_json=payload,
                    )
                )
            else:
                row.state = record.state.value
                row.version = record.version
                row.record_json = payload
                row.updated_at = datetime.now(timezone.utc)
            session.commit()

    def _ticket_from_row(self, row: ReviewTicketRecord) -> ReviewTicket:
        return ReviewTicket(
            invariant_id=row.invariant_id,
            status=ReviewStatus(row.status),
            adversary_scores=cast(dict[str, float], json.loads(row.adversary_scores_json)),
            checklist_complete=row.checklist_complete,
            reviewer=row.reviewer,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _save_review_ticket(self, ticket: ReviewTicket) -> None:
        with self._session() as session:
            row = session.get(ReviewTicketRecord, ticket.invariant_id)
            if row is None:
                session.add(
                    ReviewTicketRecord(
                        invariant_id=ticket.invariant_id,
                        status=ticket.status.value,
                        adversary_scores_json=json.dumps(ticket.adversary_scores),
                        checklist_complete=ticket.checklist_complete,
                        reviewer=ticket.reviewer,
                        notes=ticket.notes,
                        created_at=ticket.created_at,
                        updated_at=ticket.updated_at,
                    )
                )
            else:
                row.status = ticket.status.value
                row.adversary_scores_json = json.dumps(ticket.adversary_scores)
                row.checklist_complete = ticket.checklist_complete
                row.reviewer = ticket.reviewer
                row.notes = ticket.notes
                row.updated_at = ticket.updated_at
            session.commit()

    def _enqueue_review(self, invariant_id: str, adversary_scores: dict[str, float]) -> ReviewTicket:
        ticket = ReviewTicket(invariant_id=invariant_id, adversary_scores=adversary_scores)
        self._save_review_ticket(ticket)
        return ticket

    def _log_audit(self, actor: str, action: str, resource_id: str, detail: dict[str, Any] | None = None) -> None:
        detail = detail or {}
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._session() as session:
            session.add(
                AuditEventRecord(
                    timestamp=timestamp,
                    actor=actor,
                    action=action,
                    resource_id=resource_id,
                    detail_json=json.dumps(detail),
                )
            )
            session.commit()

    def export_audit_log(self) -> list[dict[str, Any]]:
        from sqlalchemy import select

        with self._session() as session:
            rows = session.scalars(select(AuditEventRecord).order_by(AuditEventRecord.id)).all()
            return [
                {
                    "timestamp": row.timestamp,
                    "actor": row.actor,
                    "action": row.action,
                    "resource_id": row.resource_id,
                    "detail": cast(dict[str, Any], json.loads(row.detail_json)),
                }
                for row in rows
            ]

    def export_audit_log_since(self, after_id: int) -> tuple[list[dict[str, Any]], int]:
        from sqlalchemy import select

        with self._session() as session:
            rows = session.scalars(
                select(AuditEventRecord).where(AuditEventRecord.id > after_id).order_by(AuditEventRecord.id)
            ).all()
            events = [
                {
                    "timestamp": row.timestamp,
                    "actor": row.actor,
                    "action": row.action,
                    "resource_id": row.resource_id,
                    "detail": cast(dict[str, Any], json.loads(row.detail_json)),
                }
                for row in rows
            ]
            new_watermark = rows[-1].id if rows else after_id
            return events, new_watermark

    def flush_audit_sink(self) -> dict[str, Any]:
        events, new_watermark = self.export_audit_log_since(self._watermark.value)
        result = flush_audit_events(self._audit_sink, events)
        if events and result.get("flushed"):
            self._watermark.advance(new_watermark)
        result["watermark"] = self._watermark.value
        result["exported_count"] = len(events)
        return result

    def audit_status(self) -> dict[str, Any]:
        from sqlalchemy import func, select

        watermark = self._watermark.value
        with self._session() as session:
            total = int(session.scalar(select(func.count()).select_from(AuditEventRecord)) or 0)
            pending = int(
                session.scalar(
                    select(func.count())
                    .select_from(AuditEventRecord)
                    .where(AuditEventRecord.id > watermark)
                )
                or 0
            )
        return {
            "event_count": total,
            "watermark": watermark,
            "pending_export": pending,
            "sink_configured": self._audit_sink is not None,
        }

    def get_lifecycle(self, invariant_id: str) -> ArtifactRecord:
        with self._session() as session:
            row = session.get(ArtifactLifecycleRecord, invariant_id)
            if row is None:
                raise KeyError(invariant_id)
            return ArtifactRecord.model_validate_json(row.record_json)

    def transition_lifecycle(
        self, invariant_id: str, to_state: LifecycleState, actor: str, reason: str
    ) -> ArtifactRecord:
        record = self.get_lifecycle(invariant_id)
        ts = datetime.now(timezone.utc).isoformat()
        updated = self._lifecycle.transition(record, to_state, actor, reason, ts)
        self._save_artifact_record(updated)
        self.append_lifecycle_event(
            invariant_id, record.state.value, to_state.value, actor, reason
        )
        self._log_audit(actor, "lifecycle.transition", invariant_id, {"to_state": to_state.value, "reason": reason})
        return updated

    def register(self, package: dict[str, Any]) -> str:
        from cfi_contributor.adversaries import ReleaseGateAdversaries
        from cfi_registry.validation import validate_and_parse_package

        cfi = validate_and_parse_package(package)
        with self._session() as session:
            if session.get(CFIRecord, cfi.id):
                raise ValueError("Duplicate invariant id")
            session.add(
                CFIRecord(
                    invariant_id=cfi.id,
                    package_json=json.dumps(package),
                    signature=str(package.get("signature", "")),
                )
            )
            session.commit()
        record = ArtifactRecord(
            invariant_id=cfi.id, state=LifecycleState.REVIEWED, version="1.0.0"
        )
        self._save_artifact_record(record)
        scores = ReleaseGateAdversaries().score_cfi(cfi)
        self._enqueue_review(
            cfi.id,
            {
                "source_attribution": scores.source_attribution,
                "reconstruction": scores.reconstruction,
                "linkability": scores.linkability,
            },
        )
        self._log_audit("system", "cfi.registered", cfi.id, {"state": LifecycleState.REVIEWED.value})
        return cfi.id

    def get(self, invariant_id: str) -> dict[str, Any]:
        with self._session() as session:
            row = session.get(CFIRecord, invariant_id)
            if row is None:
                raise KeyError(invariant_id)
            return cast(dict[str, Any], json.loads(row.package_json))

    def publish_cohort(self, manifest: CohortManifest) -> str:
        if manifest.frozen:
            raise ValueError("Manifest already frozen")
        manifest = manifest.model_copy(update={"frozen": True})
        with self._session() as session:
            if session.get(CohortManifestRecord, manifest.aggregation_epoch):
                raise ValueError("Epoch already published")
            session.add(
                CohortManifestRecord(
                    aggregation_epoch=manifest.aggregation_epoch,
                    manifest_json=manifest.model_dump_json(),
                    frozen=True,
                )
            )
            session.commit()
        self._log_audit("system", "cohort.published", manifest.invariant_id, {"epoch": manifest.aggregation_epoch})
        return manifest.aggregation_epoch

    def append_lifecycle_event(
        self,
        invariant_id: str,
        from_state: str,
        to_state: str,
        actor: str,
        reason: str,
    ) -> None:
        with self._session() as session:
            session.add(
                LifecycleHistory(
                    invariant_id=invariant_id,
                    from_state=from_state,
                    to_state=to_state,
                    actor=actor,
                    reason=reason,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def append_supersession(self, invariant_id: str, successor_id: str) -> None:
        with self._session() as session:
            session.add(
                SupersessionChain(
                    invariant_id=invariant_id,
                    successor_id=successor_id,
                    timestamp=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def list_review_queue(self) -> list[ReviewTicket]:
        from sqlalchemy import select

        with self._session() as session:
            rows = session.scalars(
                select(ReviewTicketRecord)
                .where(ReviewTicketRecord.status == ReviewStatus.PENDING.value)
                .order_by(ReviewTicketRecord.created_at)
            ).all()
            return [self._ticket_from_row(row) for row in rows]

    def get_review_ticket(self, invariant_id: str) -> ReviewTicket:
        with self._session() as session:
            row = session.get(ReviewTicketRecord, invariant_id)
            if row is None:
                raise KeyError(invariant_id)
            return self._ticket_from_row(row)

    def review_decision(self, invariant_id: str, req: Any) -> ReviewTicket:
        ticket = self.get_review_ticket(invariant_id)
        if req.status == ReviewStatus.PENDING:
            raise ValueError("Decision must move ticket out of pending")
        ticket.status = req.status
        ticket.reviewer = req.reviewer
        ticket.notes = req.notes
        ticket.checklist_complete = req.checklist_complete
        ticket.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_review_ticket(ticket)
        if req.status == ReviewStatus.APPROVED:
            self.transition_lifecycle(invariant_id, LifecycleState.ACTIVE, req.reviewer, req.notes)
        elif req.status == ReviewStatus.REJECTED:
            self.transition_lifecycle(invariant_id, LifecycleState.REVOKED, req.reviewer, req.notes)
        self._log_audit(
            req.reviewer,
            "review.decision",
            invariant_id,
            {"status": req.status.value, "checklist_complete": req.checklist_complete},
        )
        return ticket

    def supersede(self, invariant_id: str, req: Any) -> ArtifactRecord:
        try:
            self.get(req.successor_id)
        except KeyError as exc:
            raise ValueError("Successor CFI not registered") from exc
        record = self.get_lifecycle(invariant_id)
        ts = datetime.now(timezone.utc).isoformat()
        updated = self._lifecycle.supersede(record, req.successor_id, req.actor, ts)
        self._save_artifact_record(updated)
        self.append_lifecycle_event(
            invariant_id,
            record.state.value,
            LifecycleState.SUPERSEDED.value,
            req.actor,
            req.reason or f"superseded by {req.successor_id}",
        )
        self.append_supersession(invariant_id, req.successor_id)
        self._log_audit(req.actor, "cfi.superseded", invariant_id, {"successor_id": req.successor_id})
        return updated

    def stats(self) -> dict[str, int]:
        from sqlalchemy import func, select

        with self._session() as session:
            registered = session.scalar(select(func.count()).select_from(CFIRecord)) or 0
            manifests = session.scalar(select(func.count()).select_from(CohortManifestRecord)) or 0
            pending = session.scalar(
                select(func.count())
                .select_from(ReviewTicketRecord)
                .where(ReviewTicketRecord.status == ReviewStatus.PENDING.value)
            ) or 0
            active = session.scalar(
                select(func.count())
                .select_from(ArtifactLifecycleRecord)
                .where(ArtifactLifecycleRecord.state == LifecycleState.ACTIVE.value)
            ) or 0
        return {
            "registered_cfis": int(registered),
            "pending_reviews": int(pending),
            "active_cfis": int(active),
            "cohort_manifests": int(manifests),
        }
