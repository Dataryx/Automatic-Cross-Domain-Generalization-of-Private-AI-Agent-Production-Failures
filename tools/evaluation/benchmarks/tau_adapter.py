"""τ-bench-style adapter — synthetic task format, no live τ-bench dependency.

Maps external agent-benchmark JSON tasks to local CFI compile/eval plumbing.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import build_recipient_context

from benchmarks.tau_live import LIVE_ASSUMPTIONS, load_tasks

LOCAL_ASSUMPTIONS = [
    "Adapter format only; not connected to live τ-bench runtime.",
    "Uses golden exception-precedence CFI as structural template.",
]


@dataclass
class TauTaskResult:
    task_id: str
    domain: str
    compiled: bool
    notes: str = ""
    assumptions: list[str] = field(default_factory=lambda: list(LOCAL_ASSUMPTIONS))


def evaluate_tasks(path: Path | None = None) -> list[TauTaskResult]:
    cfi = build_exception_precedence_cfi()
    results: list[TauTaskResult] = []
    assumptions = list(LIVE_ASSUMPTIONS) if path is None and os.getenv("CFI_TAU_BENCH_URL") else list(LOCAL_ASSUMPTIONS)
    for task in load_tasks(path):
        domain = task.get("domain", "procurement")
        if domain in ("retail", "finance"):
            domain = "procurement"
        ctx = build_recipient_context(domain, cfi.required_mapping_roles)
        compilation = fail_closed_compile(cfi, ctx, manifest=None, seed=task.get("seed", 0))
        results.append(
            TauTaskResult(
                task_id=task["task_id"],
                domain=task.get("domain", domain),
                compiled=not compilation.abstained,
                notes=task.get("instruction", "")[:120],
                assumptions=assumptions,
            )
        )
    return results


def main() -> None:
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    results = evaluate_tasks()
    (out / "tau_adapter_results.json").write_text(
        json.dumps([r.__dict__ for r in results], indent=2)
    )
    compiled = sum(1 for r in results if r.compiled)
    print(f"τ-adapter: {compiled}/{len(results)} tasks compiled")


if __name__ == "__main__":
    main()
