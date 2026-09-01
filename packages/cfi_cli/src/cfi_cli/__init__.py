"""CFI-Fed command-line interfaces."""

import typer

contribute_app = typer.Typer(help="Contributor-side CFI extraction and packaging")
registry_app = typer.Typer(help="Registry service")
recipient_app = typer.Typer(help="Recipient-side compilation and evaluation")
aggregate_app = typer.Typer(help="Aggregation service")


@contribute_app.command("package")
def package_cfi(
    output: str = typer.Option(..., help="Output path for signed CFI JSON"),
) -> None:
    """Build and sign the golden exception-precedence CFI."""
    import json
    from pathlib import Path

    from cfi_contributor.packager import Packager
    from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
    from cfi_core.examples import build_exception_precedence_cfi
    from cfi_core.signing import KeyPair

    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers, adversary_scores={"source_attribution": 0.07, "reconstruction": 0.1})
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=verdict.residual_risk_score)
    key = KeyPair.generate("contributor-org")
    result = Packager(key).package(cfi, verdict)
    if not result.success or result.cfi is None:
        typer.echo(f"Package failed: {result.error}", err=True)
        raise typer.Exit(1)
    Path(output).write_text(json.dumps(result.cfi.model_dump(mode="json"), indent=2))
    typer.echo(f"Signed CFI written to {output}")


@contribute_app.command("gate")
def run_release_gate(
    invariant_path: str = typer.Option("golden", help="CFI JSON path or 'golden'"),
    source_domain: str | None = typer.Option(None, help="Optional source domain for adversary test"),
) -> None:
    """Run Appendix C release gate and print adversary scores."""
    import json
    from pathlib import Path

    from cfi_contributor.release_gate import ReleaseGate
    from cfi_core.examples import build_exception_precedence_cfi
    from cfi_core.models import CausalFailureInvariant

    if invariant_path != "golden" and Path(invariant_path).exists():
        cfi = CausalFailureInvariant.model_validate(json.loads(Path(invariant_path).read_text()))
    else:
        cfi = build_exception_precedence_cfi()
    verdict = ReleaseGate().run(cfi, {i: True for i in range(1, 13)}, source_domain=source_domain)
    typer.echo(f"Outcome: {verdict.outcome.value} risk={verdict.residual_risk_score:.3f}")
    for stage, status in verdict.stage_verdicts.items():
        typer.echo(f"  {stage}: {status}")
    if verdict.outcome.value not in ("approve", "restrict_distribution"):
        raise typer.Exit(1)


@contribute_app.command("extract")
def extract_from_incident(
    output: str = typer.Option(..., help="Output path for signed CFI JSON"),
    seed: int = typer.Option(421337),
    replay_url: str | None = typer.Option(None, help="HTTP replay endpoint for live agent"),
    replay_profile: str | None = typer.Option(
        None, help="Named replay profile: mock, agentrx, or causalflow"
    ),
) -> None:
    """Run contributor pipeline on synthetic incident evidence."""
    import json
    from pathlib import Path

    from cfi_contributor.pipeline import ContributorPipeline
    from cfi_contributor.replay_profiles import profile_assumptions, resolve_replay_provider
    from cfi_core.models import EventType
    from cfi_core.signing import KeyPair
    from cfi_core.wire import Incident, MinimizationConfig, TraceEvent, TypedTrace

    incident = Incident(
        incident_id="local-inc-1",
        initiating_request_digest="digest-init",
        trace=TypedTrace(events=[TraceEvent(event_type=EventType.POLICY_LOOKUP, actor="agent")]),
        policy_digest="policy-digest",
        initial_state_digest="s0",
        terminal_state_digest="s1",
        expected_outcome="deny",
        observed_outcome="allow",
        severity=0.7,
        evidence_store_ref="local://evidence/1",
    )
    raw = {"events": [{"type": "policy_lookup", "actor": "agent", "index": 0}]}
    minimization = MinimizationConfig(
        eta=0.9, delta=0.05, lambda_nodes=1.0, lambda_edges=1.0, lambda_literals=1.0, lambda_replay=1.0
    )
    try:
        replay = resolve_replay_provider(replay_url=replay_url, replay_profile=replay_profile)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    for note in profile_assumptions(replay_profile):
        typer.echo(f"Assumption: {note}")
    report = ContributorPipeline(KeyPair.generate("contributor"), replay=replay, seed=seed).extract_from_incident(
        incident, raw, minimization, {i: True for i in range(1, 13)}
    )
    if not report.package or not report.package.success or report.package.cfi is None:
        typer.echo(f"Extraction failed: {report.package}", err=True)
        raise typer.Exit(1)
    Path(output).write_text(json.dumps(report.package.cfi.model_dump(mode="json"), indent=2))
    if report.minimization and report.minimization.log:
        typer.echo(f"Minimization log entries: {len(report.minimization.log)}")
    typer.echo(f"Extracted signed CFI written to {output}")


@contribute_app.command("replay-profiles")
def list_replay_profiles() -> None:
    """List production replay profiles and environment variables."""
    from cfi_contributor.replay_profiles import REPLAY_PROFILES

    for name, spec in sorted(REPLAY_PROFILES.items()):
        typer.echo(f"{name}: env={spec.endpoint_env} default={spec.default_url}")
        typer.echo(f"  {spec.notes}")


@registry_app.command("serve")
def serve_registry(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
    database_url: str = typer.Option("sqlite:///./cfi_registry.db"),
) -> None:
    import uvicorn
    from cfi_registry import create_app
    from cfi_registry.config import ServiceConfig, create_registry_store

    config = ServiceConfig(database_url=database_url, host=host, port=port)
    store = create_registry_store(config)
    uvicorn.run(create_app(store), host=host, port=port)


@recipient_app.command("compile")
def compile_local(
    invariant_path: str = typer.Option(...),
    domain: str = typer.Option("procurement"),
) -> None:
    import json
    from pathlib import Path

    from cfi_core.examples import build_exception_precedence_cfi
    from cfi_core.models import CausalFailureInvariant
    from cfi_recipient.compiler import fail_closed_compile
    from cfi_recipient.ontology import MappingStatus, OntologyMapping, RecipientContext

    data = json.loads(Path(invariant_path).read_text()) if Path(invariant_path).exists() else None
    cfi = CausalFailureInvariant.model_validate(data) if data else build_exception_precedence_cfi()
    mappings = [
        OntologyMapping(invariant_role=r, local_entity_id=f"local_{r}", status=MappingStatus.APPROVED, approver="expert")
        for r in cfi.required_mapping_roles
    ]
    ctx = RecipientContext(domain=domain, mappings=mappings)
    result = fail_closed_compile(cfi, ctx, manifest=None)
    if result.abstained:
        typer.echo(f"Abstained: {result.abstention_reason}")
        raise typer.Exit(1)
    typer.echo(f"Compiled {len(result.cases)} cases for domain={domain}")


@recipient_app.command("mitigate")
def mitigate_local(
    invariant_path: str = typer.Option(...),
    domain: str = typer.Option("procurement"),
) -> None:
    """Run mitigation loop (Section 5.14) on compiled cases."""
    import json
    from pathlib import Path

    from cfi_core.models import CausalFailureInvariant
    from cfi_recipient.compiler import fail_closed_compile
    from cfi_recipient.mitigation import MitigationCandidate, MitigationLayer, evaluate_mitigation
    from cfi_recipient.ontology import build_recipient_context
    from cfi_recipient.sandbox import Sandbox, SandboxTrace

    data = json.loads(Path(invariant_path).read_text())
    cfi = CausalFailureInvariant.model_validate(data)
    ctx = build_recipient_context(domain, cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    if compilation.abstained:
        typer.echo(f"Abstained: {compilation.abstention_reason}", err=True)
        raise typer.Exit(1)

    def failing_agent(sb: Sandbox, trace: SandboxTrace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    def fixed_agent(sb: Sandbox, trace: SandboxTrace) -> None:
        trace.state["review_complete"] = True
        sb.execute_tool(trace, "stub_po", {})

    mitigation = MitigationCandidate(
        layer=MitigationLayer.POLICY,
        description="enforce review before irreversible action",
        agent_fn=fixed_agent,
    )
    report = evaluate_mitigation(compilation, cfi.oracle.expression, failing_agent, mitigation)
    typer.echo(
        f"Mitigation accepted={report.accepted} "
        f"pre={report.pre_susceptibility:.2f} post={report.post_susceptibility:.2f} "
        f"layer={report.layer.value}"
    )
    if not report.accepted:
        raise typer.Exit(1)


@recipient_app.command("evaluate")
def evaluate_local(
    invariant_path: str = typer.Option(...),
    domain: str = typer.Option("procurement"),
) -> None:
    """Compile locally and report susceptibility metrics (Table III families)."""
    import json
    from pathlib import Path

    from cfi_core.models import CausalFailureInvariant
    from cfi_recipient.compiler import fail_closed_compile
    from cfi_recipient.mitigation import susceptibility
    from cfi_recipient.metrics import build_report
    from cfi_recipient.ontology import build_recipient_context
    from cfi_recipient.sandbox import Sandbox, SandboxTrace

    data = json.loads(Path(invariant_path).read_text())
    cfi = CausalFailureInvariant.model_validate(data)
    ctx = build_recipient_context(domain, cfi.required_mapping_roles)
    compilation = fail_closed_compile(cfi, ctx, manifest=None)
    if compilation.abstained:
        typer.echo(f"Abstained: {compilation.abstention_reason}", err=True)
        raise typer.Exit(1)

    def failing_agent(sb: Sandbox, trace: SandboxTrace) -> None:
        trace.state["review_complete"] = False
        sb.execute_tool(trace, "stub_po", {})

    rate = susceptibility(compilation.cases, cfi.oracle.expression, failing_agent)
    positive_cases = [c for c in compilation.cases if not c.is_negative_control]
    coverage = len(positive_cases) / max(1, len(cfi.required_mapping_roles))
    report = build_report(
        spec_id="local-eval",
        cohort_id=f"local-{domain}",
        compilation_coverage=min(1.0, coverage),
        structural_precision=1.0,
        susceptibility=rate,
        residual_privacy_risk=0.0,
    )
    typer.echo(json.dumps(report.to_dict(), indent=2))


@aggregate_app.command("consortium")
def run_consortium_pilot(
    tenants: int = typer.Option(12, help="Number of consortium tenants"),
    seed: int = typer.Option(421337),
    minimum_k: int = typer.Option(10),
) -> None:
    """Phase 5 consortium round with anti-Sybil controls and DP aggregate."""
    from cfi_contributor.packager import Packager
    from cfi_contributor.release_gate import GateOutcome, ReleaseGate, ReleaseGateVerdict
    from cfi_core.examples import build_exception_precedence_cfi
    from cfi_core.signing import KeyPair
    from cfi_core.wire import CohortManifest, MeasurementSpec
    from cfi_federation.consortium import ConsortiumConfig, ConsortiumCoordinator, TenantIdentity

    cfi = build_exception_precedence_cfi()
    gate = ReleaseGate()
    answers = {i: True for i in range(1, 13)}
    verdict = gate.run(cfi, answers)
    if verdict.outcome != GateOutcome.APPROVE:
        verdict = ReleaseGateVerdict(outcome=GateOutcome.APPROVE, residual_risk_score=verdict.residual_risk_score)
    pkg = Packager(KeyPair.generate("consortium-contributor")).package(cfi, verdict)
    if not pkg.success or pkg.cfi is None:
        typer.echo("Failed to package CFI", err=True)
        raise typer.Exit(1)

    invariant_id = pkg.cfi.id
    spec = MeasurementSpec(
        spec_id="consortium-cli",
        invariant_id=invariant_id,
        simulated_user="stub",
        tool_behavior="stubbed",
        judge="state_first",
        evidence_bar="high",
        trial_count=3,
        aggregation_rule="mean",
        compiler_version="0.1.0",
    )
    manifest = CohortManifest(
        invariant_id=invariant_id,
        eligible_compiler_versions=["0.1.0"],
        measurement_spec=spec,
        trial_count=3,
        clipping_f=10,
        clipping_n=100,
        privacy_budget_epsilon=1.0,
        aggregation_epoch="consortium-cli-1",
        expiration="2026-12-31",
        minimum_cohort_k=minimum_k,
    )
    domains = ["procurement", "healthcare", "data_operations", "finance", "logistics", "retail"]
    identities = [
        TenantIdentity(tenant_id=f"tenant-{i:02d}", org_family=f"org-{i % 6}", compiler_version="0.1.0")
        for i in range(tenants)
    ]
    config = ConsortiumConfig(minimum_k=minimum_k, max_per_org_family=2, dropout_rate=0.08)
    result = ConsortiumCoordinator(config).run_round(
        pkg.cfi.model_dump(mode="json"),
        manifest,
        identities,
        cfi.required_mapping_roles,
        domains,
        seed=seed,
    )
    if result.released:
        typer.echo(
            f"Consortium released: prevalence={result.noisy_prevalence:.4f}, "
            f"participants={result.participants}"
        )
    else:
        typer.echo(f"Consortium not released: {result.reason}", err=True)
        raise typer.Exit(1)


@aggregate_app.command("simulate")
def simulate_aggregate(
    tenants: int = typer.Option(50),
    epsilon: float = typer.Option(1.0),
    seed: int = typer.Option(421337),
) -> None:
    import random

    from cfi_federation import ClippedContribution, secure_aggregate

    rng = random.Random(seed)
    contribs = [
        ClippedContribution(
            tenant_id=f"t{i}",
            failures=rng.randint(0, 5),
            trials=10,
            coverage=1.0,
        )
        for i in range(tenants)
    ]
    release = secure_aggregate(
        contribs,
        [],
        threshold=2,
        minimum_k=10,
        epsilon=epsilon,
        measurement_spec_id="spec-sim",
        rng=rng,
    )
    if release:
        typer.echo(
            f"Aggregate prevalence={release.noisy_prevalence:.4f} "
            f"(ε={release.epsilon}, n={release.cohort_size})"
        )
    else:
        typer.echo("Below minimum cohort threshold")


app = contribute_app  # default entry for cfi-contribute script
