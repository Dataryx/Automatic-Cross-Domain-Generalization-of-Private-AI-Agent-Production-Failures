"""Hypothesis property test for DP prevalence bounds."""

from hypothesis import given, settings
from hypothesis import strategies as st

from cfi_federation import dp_binary_prevalence


@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=1), min_size=1, max_size=50), st.floats(min_value=0.1, max_value=5.0))
def test_dp_prevalence_bounded(flags: list[int], epsilon: float) -> None:
    rate = dp_binary_prevalence(flags, epsilon=epsilon, rng=None)
    assert 0.0 <= rate <= 1.0
