"""PostgreSQL append-only persistence for registry and lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from cfi_core.wire import CohortManifest
from cfi_governance import ArtifactRecord, LifecycleManager, LifecycleState
from cfi_governance.review import ReviewQueue, ReviewTicket


class Base(DeclarativeBase):
    pass


class CFIRecord(Base):
    __tablename__ = "cfi_records"

    invariant_id: Mapped[str] = mapped_column(String, primary_key=True)
    package_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, default="cfi/1.0")
    signature: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


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


class PostgresRegistryStore:
    """Append-only registry backing store."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, future=True)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._lifecycle = LifecycleManager()
        self._records: dict[str, ArtifactRecord] = {}
        self._review = ReviewQueue()

    def _session(self) -> Session:
        return self._session_factory()

    def close(self) -> None:
        self._engine.dispose()

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
        self.append_lifecycle_event(
            invariant_id, record.state.value, to_state.value, actor, reason
        )
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
        self._records[cfi.id] = ArtifactRecord(
            invariant_id=cfi.id, state=LifecycleState.REVIEWED, version="1.0.0"
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
        with self._session() as session:
            row = session.get(CFIRecord, invariant_id)
            if row is None:
                raise KeyError(invariant_id)
            return json.loads(row.package_json)

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
        return self._review.list_pending()

    def review_decision(self, invariant_id: str, req: Any) -> ReviewTicket:
        ticket = self._review.decide(
            invariant_id,
            req.status,
            req.reviewer,
            req.notes,
            req.checklist_complete,
        )
        if req.status.value == "approved":
            self.transition_lifecycle(invariant_id, LifecycleState.ACTIVE, req.reviewer, req.notes)
        elif req.status.value == "rejected":
            self.transition_lifecycle(invariant_id, LifecycleState.REVOKED, req.reviewer, req.notes)
        return ticket
