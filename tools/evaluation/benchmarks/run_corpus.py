"""Synthetic benchmark corpus evaluation (tau-bench style, no live agents)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import build_recipient_context

CORPUS = Path(__file__).resolve().parent / "corpus" / "incidents.json"


@dataclass
class CorpusResult:
    incident_id: str
    family: str
    domain: str
    compiled: bool
    attribution_risk: float
    assumptions: list[str] = field(default_factory=lambda: [
        "Synthetic corpus; not tau-bench or private production data.",
        "Compilation uses golden exception-precedence invariant template.",
    ])


def load_corpus(path: Path | None = None) -> list[dict]:
    return json.loads((path or CORPUS).read_text(encoding="utf-8"))


def evaluate_corpus(path: Path | None = None) -> list[CorpusResult]:
    cfi = build_exception_precedence_cfi()
    adv = ReleaseGateAdversaries()
    report = adv.score_cfi(cfi)
    results: list[CorpusResult] = []
    for row in load_corpus(path):
        domain = row["domain"]
        if domain == "retail":
            domain = "procurement"
        if domain == "finance":
            domain = "procurement"
        ctx = build_recipient_context(domain, cfi.required_mapping_roles)
        compilation = fail_closed_compile(cfi, ctx, manifest=None)
        results.append(
            CorpusResult(
                incident_id=row["incident_id"],
                family=row["family"],
                domain=row["domain"],
                compiled=not compilation.abstained,
                attribution_risk=report.source_attribution,
            )
        )
    return results


def main() -> None:
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    results = evaluate_corpus()
    payload = [r.__dict__ for r in results]
    (out / "corpus_results.json").write_text(json.dumps(payload, indent=2))
    compiled = sum(1 for r in results if r.compiled)
    print(f"Corpus eval: {compiled}/{len(results)} compiled")
    for r in results:
        print(f"  {r.incident_id} ({r.family}/{r.domain}): compiled={r.compiled}")


if __name__ == "__main__":
    main()
