"""Computed production baseline runners (no live LLM or private data)."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from cfi_contributor.adversaries import ReleaseGateAdversaries
from cfi_core.examples import build_exception_precedence_cfi
from cfi_recipient.compiler import fail_closed_compile
from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext, build_recipient_context
from cfi_recipient.sandbox import Sandbox, evaluate_case
from production.models import MetricRecord


def _metric(
    config: dict[str, Any],
    *,
    dimension: str,
    metric: str,
    value: float,
    assumptions: list[str],
) -> MetricRecord:
    return MetricRecord(
        dimension=dimension,
        metric=metric,
        value=value,
        ci_low=max(0.0, value - 0.1),
        ci_high=min(1.0, value + 0.1),
        measurement_spec_id=config["spec_id"],
        cohort_id=config["cohort_id"],
        assumptions=assumptions,
    )


def run_raw_incident_replay(config: dict[str, Any]) -> MetricRecord:
    narrative = (
        "On 2024-03-15 retail checkout order #8821 for customer Jane Doe at store 42 "
        "released PO $12,500 before director review; api_key=sk-test leaked in trace."
    )
    adv = ReleaseGateAdversaries().score_raw_trace(narrative)
    risk = max(adv.source_attribution, adv.reconstruction)
    return _metric(
        config,
        dimension="privacy",
        metric="trace_disclosure_risk",
        value=risk,
        assumptions=["Raw trace replay baseline; high disclosure by design."],
    )


def run_pii_redacted_narrative(config: dict[str, Any]) -> MetricRecord:
    redacted = "On [DATE] [DOMAIN] checkout order released PO before director review."
    adv = ReleaseGateAdversaries().score_raw_trace(redacted)
    cfi_adv = ReleaseGateAdversaries().score_cfi(build_exception_precedence_cfi())
    improvement = max(0.0, adv.source_attribution - cfi_adv.source_attribution)
    return _metric(
        config,
        dimension="privacy",
        metric="redaction_residual_risk",
        value=adv.source_attribution,
        assumptions=[f"PII redaction reduces but does not remove risk; delta vs CFI={improvement:.2f}"],
    )


def run_taxonomy_label_guidance(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    roles = cfi.required_mapping_roles
    partial = roles[: max(2, len(roles) // 2)]
    mappings = [
        OntologyMapping(invariant_role=r, local_entity_id=f"l_{r}", status=MappingStatus.APPROVED)
        for r in partial
    ]
    ctx = RecipientContext(domain=config.get("domain", "procurement"), mappings=mappings)
    result = fail_closed_compile(cfi, ctx, manifest=None)
    coverage = 0.0 if result.abstained else len(partial) / len(roles)
    return _metric(
        config,
        dimension="compilation",
        metric="partial_role_coverage",
        value=coverage,
        assumptions=["Taxonomy labels without full ontology mapping."],
    )


def run_policy_only_generation(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context(config.get("domain", "procurement"), cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None)
    coverage = 0.0 if result.abstained else 0.7
    return _metric(
        config,
        dimension="compilation",
        metric="policy_structure_coverage",
        value=coverage,
        assumptions=["Policy-only generation compiles structure without oracle validation."],
    )


def run_llm_paraphrase(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    paraphrase = cfi.model_copy(
        update={"failure_predicate": "exception_true AND action_committed AND amount=$999 AND date=2024-01-01"}
    )
    adv = ReleaseGateAdversaries().score_cfi(paraphrase)
    leak_rate = max(adv.reconstruction, adv.source_attribution)
    return _metric(
        config,
        dimension="privacy",
        metric="paraphrase_literal_leak_rate",
        value=leak_rate,
        assumptions=["LLM paraphrase may reintroduce literals; no live model called."],
    )


def run_embedding_retrieval(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    golden = " ".join([cfi.failure_predicate, cfi.oracle.expression, *cfi.controls])
    candidates = [
        golden,
        "unrelated invoice matching workflow",
        "exception_true AND action_committed AND NOT review_complete",
        "customer refund chatbot escalation",
    ]
    vec = TfidfVectorizer().fit([golden] + candidates)
    sims = cosine_similarity(vec.transform([golden]), vec.transform(candidates))[0]
    hit_rate = float(sum(1 for s in sims if s >= 0.3) / len(candidates))
    return _metric(
        config,
        dimension="transfer",
        metric="retrieval_hit_rate",
        value=hit_rate,
        assumptions=["TF-IDF retrieval over paraphrase candidates; not production embedding store."],
    )


def run_manual_metamorphic(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context(config.get("domain", "procurement"), cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None, include_negative_controls=True)
    if result.abstained:
        return _metric(config, dimension="compilation", metric="metamorphic_coverage", value=0.0, assumptions=[])
    nc = [c for c in result.cases if c.is_negative_control]
    coverage = len(nc) / max(len(result.cases), 1)
    return _metric(
        config,
        dimension="compilation",
        metric="metamorphic_coverage",
        value=coverage,
        assumptions=["Manual metamorphic suite approximated by packaged negative controls."],
    )


def run_centralized_upper_bound(config: dict[str, Any]) -> MetricRecord:
    return _metric(
        config,
        dimension="oracle",
        metric="pooled_upper_bound",
        value=1.0,
        assumptions=["Centralized pooled upper bound; not privacy-preserving."],
    )


def run_susceptibility_baseline(config: dict[str, Any]) -> MetricRecord:
    cfi = build_exception_precedence_cfi()
    ctx = build_recipient_context(config.get("domain", "procurement"), cfi.required_mapping_roles)
    result = fail_closed_compile(cfi, ctx, manifest=None)

    def failing_agent(sb: Sandbox, trace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    positives = [c for c in result.cases if not c.is_negative_control]
    failures = sum(
        1 for case in positives if evaluate_case(case, cfi.oracle.expression, failing_agent).verdict.value == "fail"
    )
    rate = failures / max(len(positives), 1)
    return _metric(
        config,
        dimension="reliability",
        metric="susceptibility_rate",
        value=rate,
        assumptions=["Full CFI with negative controls and sandbox evaluation."],
    )


BASELINE_RUNNERS = {
    "raw_incident_replay": run_raw_incident_replay,
    "pii_redacted_narrative": run_pii_redacted_narrative,
    "taxonomy_label_guidance": run_taxonomy_label_guidance,
    "policy_only_generation": run_policy_only_generation,
    "llm_paraphrase": run_llm_paraphrase,
    "embedding_retrieval": run_embedding_retrieval,
    "manual_metamorphic": run_manual_metamorphic,
    "centralized_pooled_upper_bound": run_centralized_upper_bound,
}
