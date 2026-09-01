"""Human review queue for release-gate decisions (Appendix C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_GENERALIZATION = "needs_generalization"


@dataclass
class ReviewTicket:
    invariant_id: str
    status: ReviewStatus = ReviewStatus.PENDING
    adversary_scores: dict[str, float] = field(default_factory=dict)
    checklist_complete: bool = False
    reviewer: str | None = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ReviewQueue:
    def __init__(self) -> None:
        self._tickets: dict[str, ReviewTicket] = {}

    def enqueue(self, invariant_id: str, adversary_scores: dict[str, float] | None = None) -> ReviewTicket:
        ticket = ReviewTicket(
            invariant_id=invariant_id,
            adversary_scores=adversary_scores or {},
        )
        self._tickets[invariant_id] = ticket
        return ticket

    def list_pending(self) -> list[ReviewTicket]:
        return [t for t in self._tickets.values() if t.status == ReviewStatus.PENDING]

    def get(self, invariant_id: str) -> ReviewTicket:
        if invariant_id not in self._tickets:
            raise KeyError(invariant_id)
        return self._tickets[invariant_id]

    def decide(
        self,
        invariant_id: str,
        status: ReviewStatus,
        reviewer: str,
        notes: str = "",
        checklist_complete: bool = True,
    ) -> ReviewTicket:
        ticket = self.get(invariant_id)
        if status == ReviewStatus.PENDING:
            raise ValueError("Decision must move ticket out of pending")
        ticket.status = status
        ticket.reviewer = reviewer
        ticket.notes = notes
        ticket.checklist_complete = checklist_complete
        ticket.updated_at = datetime.now(timezone.utc).isoformat()
        return ticket
