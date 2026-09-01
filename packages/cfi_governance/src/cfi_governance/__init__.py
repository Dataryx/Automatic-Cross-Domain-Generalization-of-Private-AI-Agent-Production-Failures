"""Governance: lifecycle state machine, severity, disclosure, revocation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LifecycleState(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    RESTRICTED = "restricted"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    RETIRED = "retired"


VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.DRAFT: {LifecycleState.REVIEWED, LifecycleState.RETIRED},
    LifecycleState.REVIEWED: {LifecycleState.RESTRICTED, LifecycleState.ACTIVE, LifecycleState.DRAFT},
    LifecycleState.RESTRICTED: {LifecycleState.ACTIVE, LifecycleState.REVOKED},
    LifecycleState.ACTIVE: {LifecycleState.SUPERSEDED, LifecycleState.REVOKED},
    LifecycleState.SUPERSEDED: {LifecycleState.ACTIVE, LifecycleState.RETIRED},
    LifecycleState.REVOKED: {LifecycleState.RETIRED},
    LifecycleState.RETIRED: set(),
}


class LifecycleEvent(BaseModel):
    from_state: LifecycleState
    to_state: LifecycleState
    actor: str
    reason: str
    timestamp: str


class ArtifactRecord(BaseModel):
    invariant_id: str
    state: LifecycleState = LifecycleState.DRAFT
    version: str
    history: list[LifecycleEvent] = Field(default_factory=list)
    supersession_chain: list[str] = Field(default_factory=list)
    measurement_spec_pins: list[str] = Field(default_factory=list)


class SeverityScore(BaseModel):
    impact: float
    reversibility: float
    autonomy: float
    exploitability: float
    required_access: float
    detectability: float
    estimated_prevalence: float

    @property
    def composite(self) -> float:
        return (
            self.impact * 0.25
            + (1 - self.reversibility) * 0.2
            + self.autonomy * 0.15
            + self.exploitability * 0.15
            + self.required_access * 0.1
            + (1 - self.detectability) * 0.1
            + self.estimated_prevalence * 0.05
        )


class LifecycleManager:
    def transition(self, record: ArtifactRecord, to_state: LifecycleState, actor: str, reason: str, ts: str) -> ArtifactRecord:
        allowed = VALID_TRANSITIONS.get(record.state, set())
        if to_state not in allowed:
            raise ValueError(f"Invalid transition {record.state} -> {to_state}")
        event = LifecycleEvent(
            from_state=record.state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            timestamp=ts,
        )
        record.history.append(event)
        record.state = to_state
        return record

    def supersede(self, record: ArtifactRecord, new_id: str, actor: str, ts: str) -> ArtifactRecord:
        record.supersession_chain.append(new_id)
        return self.transition(record, LifecycleState.SUPERSEDED, actor, f"superseded by {new_id}", ts)

    def revoke(self, record: ArtifactRecord, actor: str, reason: str, ts: str) -> ArtifactRecord:
        return self.transition(record, LifecycleState.REVOKED, actor, reason, ts)
