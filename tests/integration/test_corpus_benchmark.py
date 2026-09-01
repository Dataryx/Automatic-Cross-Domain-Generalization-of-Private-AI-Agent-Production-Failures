"""Benchmark corpus evaluation tests."""

from eval.benchmarks.run_corpus import evaluate_corpus, load_corpus


def test_corpus_loads() -> None:
    rows = load_corpus()
    assert len(rows) >= 5


def test_corpus_compiles_across_domains() -> None:
    results = evaluate_corpus()
    assert all(r.compiled for r in results)
