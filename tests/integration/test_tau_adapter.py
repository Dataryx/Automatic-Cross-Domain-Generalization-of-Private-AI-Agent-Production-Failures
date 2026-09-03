"""τ-bench adapter tests."""

from benchmarks.tau_adapter import evaluate_tasks, load_tasks


def test_tau_tasks_load() -> None:
    tasks = load_tasks()
    assert len(tasks) >= 4


def test_tau_adapter_compiles() -> None:
    results = evaluate_tasks()
    assert all(r.compiled for r in results)
