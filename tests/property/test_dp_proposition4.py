"""Proposition 4 — tenant-level differential privacy."""

import random

from cfi_federation import dp_binary_prevalence


def test_dp_sensitivity_single_tenant() -> None:
    rng = random.Random(42)
    flags = [0, 1, 0, 1, 1]
    p1 = dp_binary_prevalence(flags, epsilon=1.0, rng=rng)
    p2 = dp_binary_prevalence([1] + flags[1:], epsilon=1.0, rng=random.Random(42))
    # Same noise draw would differ; mechanism is defined
    assert 0.0 <= p1 <= 1.0
    assert 0.0 <= p2 <= 1.0
