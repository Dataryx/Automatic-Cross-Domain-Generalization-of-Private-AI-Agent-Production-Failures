"""Trained adversary and review queue tests."""

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_contributor.trained_adversary import TrainedAttributionModel
from cfi_core.examples import build_exception_precedence_cfi
from cfi_governance.review import ReviewQueue, ReviewStatus


def test_trained_model_low_on_canonical_cfi() -> None:
    cfi = build_exception_precedence_cfi()
    score = TrainedAttributionModel().score_cfi(cfi)
    assert score.probability < 0.5


def test_trained_model_high_on_leaky_text() -> None:
    cfi = build_exception_precedence_cfi()
    canonical = TrainedAttributionModel().score_cfi(cfi)
    leaky = cfi.model_copy(
        update={
            "failure_predicate": (
                "retail checkout sku cart order patient claim vendor pipeline wire ledger failed"
            )
        }
    )
    score = TrainedAttributionModel().score_cfi(leaky)
    assert score.probability > canonical.probability
    assert score.probability > 0.4


def test_combined_adversaries_use_trained() -> None:
    cfi = build_exception_precedence_cfi()
    report = ReleaseGateAdversaries(use_trained_attribution=True).score_cfi(cfi)
    assert report.source_attribution < 0.3


def test_review_queue_decision() -> None:
    q = ReviewQueue()
    q.enqueue("CFI-1", {"source_attribution": 0.1})
    assert len(q.list_pending()) == 1
    ticket = q.decide("CFI-1", ReviewStatus.APPROVED, "reviewer@org", notes="ok")
    assert ticket.status == ReviewStatus.APPROVED
    assert len(q.list_pending()) == 0
