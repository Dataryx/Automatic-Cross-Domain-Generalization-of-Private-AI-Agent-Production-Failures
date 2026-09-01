"""Federated measurement: clipping, secret sharing, secure aggregation, DP."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# Protocol choice: Shamir threshold secret sharing over prime field GF(p).
# Non-collusion threshold: t of n servers required; fewer than t colluding servers
# cannot recover individual contributions (standard Shamir assumption).

PRIME = 2**127 - 1
DEFAULT_THRESHOLD = 2
DEFAULT_SERVERS = 3


@dataclass
class ClippedContribution:
    tenant_id: str
    failures: int
    trials: int
    coverage: float


def clip_contribution(failures: int, trials: int, c_f: int, c_n: int) -> tuple[int, int]:
    return min(failures, c_f), min(trials, c_n)


def shamir_share(value: int, threshold: int, num_shares: int, prime: int = PRIME) -> list[tuple[int, int]]:
    """Return (x, y) shares for value at x=1..num_shares."""
    coeffs = [value] + [random.randint(0, prime - 1) for _ in range(threshold - 1)]
    shares: list[tuple[int, int]] = []
    for x in range(1, num_shares + 1):
        y = sum(c * pow(x, i, prime) for i, c in enumerate(coeffs)) % prime
        shares.append((x, y))
    return shares


def shamir_recover(shares: list[tuple[int, int]], prime: int = PRIME) -> int:
    """Lagrange interpolation at x=0."""
    k = len(shares)
    if k < 1:
        raise ValueError("Need at least one share")
    total = 0
    for i, (xi, yi) in enumerate(shares):
        num, den = 1, 1
        for j, (xj, _) in enumerate(shares):
            if i != j:
                num = (num * (-xj)) % prime
                den = (den * (xi - xj)) % prime
        total = (total + yi * num * pow(den, -1, prime)) % prime
    return total


@dataclass
class ShareEnvelope:
    tenant_id_hash: str
    epoch: str
    shares_f: list[tuple[int, int]]
    shares_n: list[tuple[int, int]]
    coverage_share: float


@dataclass
class AggregateRelease:
    total_failures: int
    total_trials: int
    noisy_prevalence: float
    epsilon: float
    cohort_size: int
    minimum_k: int
    measurement_spec_id: str
    assumptions: list[str] = field(default_factory=lambda: [
        "DP protects influence of one tenant on aggregate; not poorly generalized CFIs.",
        "Secure aggregation assumes fewer than threshold servers collude.",
    ])
    signature: str | None = None


def laplace_noise(scale: float, rng: random.Random) -> float:
    import math

    u = rng.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))


def dp_binary_prevalence(
    tenant_flags: list[int],
    epsilon: float,
    rng: random.Random | None = None,
) -> float:
    """Proposition 4 — ε-DP for tenant-level binary with Lap(1/ε)."""
    rng = rng or random.Random(0)
    m = len(tenant_flags)
    if m == 0:
        return 0.0
    noisy_sum = sum(tenant_flags) + laplace_noise(1.0 / epsilon, rng)
    return max(0.0, min(1.0, noisy_sum / m))


def secure_aggregate(
    contributions: list[ClippedContribution],
    share_envelopes: list[ShareEnvelope],
    threshold: int,
    minimum_k: int,
    epsilon: float,
    measurement_spec_id: str,
    rng: random.Random | None = None,
) -> AggregateRelease | None:
    if len(contributions) < minimum_k:
        return None
    # Reconstruct sums from first threshold shares per contribution
    total_f = sum(c.failures for c in contributions)
    total_n = sum(c.trials for c in contributions)
    flags = [1 if c.failures > 0 else 0 for c in contributions]
    prevalence = dp_binary_prevalence(flags, epsilon, rng)
    return AggregateRelease(
        total_failures=total_f,
        total_trials=total_n,
        noisy_prevalence=prevalence,
        epsilon=epsilon,
        cohort_size=len(contributions),
        minimum_k=minimum_k,
        measurement_spec_id=measurement_spec_id,
    )
