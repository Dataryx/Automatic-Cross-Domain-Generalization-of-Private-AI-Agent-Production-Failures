"""τ-bench live loader tests."""

from eval.benchmarks import tau_live
from eval.benchmarks.tau_adapter import evaluate_tasks
from eval.benchmarks.tau_live import load_tasks


def test_tau_live_load_tasks_from_url(monkeypatch) -> None:
    monkeypatch.setenv("CFI_TAU_BENCH_URL", "http://stub/v1/tasks")

    def fake_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        class Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> list[dict]:
                return [{"task_id": "live-1", "domain": "procurement", "instruction": "x", "seed": 1}]

        return Resp()

    monkeypatch.setattr(tau_live.httpx, "get", fake_get)
    tasks = load_tasks()
    assert tasks[0]["task_id"] == "live-1"


def test_tau_live_evaluate_tasks(monkeypatch) -> None:
    monkeypatch.setenv("CFI_TAU_BENCH_URL", "http://stub/v1/tasks")

    def fake_get(url: str, **kwargs):  # type: ignore[no-untyped-def]
        class Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> list[dict]:
                return [{"task_id": "live-2", "domain": "healthcare", "instruction": "y", "seed": 2}]

        return Resp()

    monkeypatch.setattr(tau_live.httpx, "get", fake_get)
    results = evaluate_tasks()
    assert results[0].compiled
    assert "Remote task fetch" in results[0].assumptions[0]
