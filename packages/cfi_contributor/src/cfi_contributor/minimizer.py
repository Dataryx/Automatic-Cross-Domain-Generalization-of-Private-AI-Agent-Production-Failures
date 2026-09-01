"""Algorithm 2 — Typed causal-core minimization (ddmin-style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class MinimizationLogEntry:
    action: str  # accept | reject
    removed_elements: list[str]
    reason: str


@dataclass
class MinimizationResult(Generic[T]):
    core: T
    log: list[MinimizationLogEntry] = field(default_factory=list)


def typed_causal_core_minimization(
    candidate: set[str],
    failure_preserving: Callable[[set[str]], bool],
    type_checker: Callable[[set[str]], bool],
    privacy_cost: Callable[[set[str]], float],
) -> MinimizationResult[set[str]]:
    """Algorithm 2 — returns locally minimal core with auditable log."""
    c = set(candidate)
    log: list[MinimizationLogEntry] = []
    n = 2
    while len(c) >= 2:
        elements = sorted(c, key=lambda e: -privacy_cost({e}))
        partitions: list[list[str]] = [[] for _ in range(n)]
        for i, el in enumerate(elements):
            partitions[i % n].append(el)
        reduced = False
        for delta in sorted(partitions, key=lambda p: -sum(privacy_cost({e}) for e in p)):
            if not delta:
                continue
            c_prime = c - set(delta)
            if type_checker(c_prime) and failure_preserving(c_prime):
                log.append(MinimizationLogEntry(action="accept", removed_elements=delta, reason="preserves_failure"))
                c = c_prime
                n = max(2, n - 1)
                reduced = True
                break
            log.append(
                MinimizationLogEntry(
                    action="reject",
                    removed_elements=delta,
                    reason="failed_preservation_or_type",
                )
            )
        if not reduced:
            if n >= len(c):
                break
            n = min(2 * n, len(c))
    return MinimizationResult(core=c, log=log)
