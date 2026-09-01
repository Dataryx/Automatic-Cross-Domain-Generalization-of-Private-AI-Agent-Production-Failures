"""Privacy accountant for composition limits and sparse slice suppression."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BudgetEntry:
    epsilon: float
    delta: float
    cohort_id: str
    epoch: str


@dataclass
class AccountantVerdict:
    allowed: bool
    remaining_epsilon: float
    reason: str = ""


class PrivacyAccountant:
    def __init__(self, total_epsilon: float, min_cohort_for_slice: int = 5) -> None:
        self._total = total_epsilon
        self._spent = 0.0
        self._min_slice = min_cohort_for_slice
        self._history: list[BudgetEntry] = field(default_factory=list)  # type: ignore[misc]

    def __post_init__(self) -> None:
        self._history = []

    def request_release(self, epsilon: float, cohort_size: int, cohort_id: str, epoch: str) -> AccountantVerdict:
        if cohort_size < self._min_slice:
            return AccountantVerdict(
                allowed=False,
                remaining_epsilon=self._total - self._spent,
                reason="sparse_slice_suppressed",
            )
        if self._spent + epsilon > self._total:
            return AccountantVerdict(
                allowed=False,
                remaining_epsilon=self._total - self._spent,
                reason="budget_exhausted",
            )
        self._spent += epsilon
        self._history.append(BudgetEntry(epsilon=epsilon, delta=0.0, cohort_id=cohort_id, epoch=epoch))
        return AccountantVerdict(allowed=True, remaining_epsilon=self._total - self._spent)
