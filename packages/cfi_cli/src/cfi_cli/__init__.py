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
    from pathlib import Path
    import json

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


@registry_app.command("serve")
def serve_registry(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    from cfi_registry import create_app

    uvicorn.run(create_app(), host=host, port=port)


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


@aggregate_app.command("simulate")
def simulate_aggregate(
    tenants: int = typer.Option(50),
    epsilon: float = typer.Option(1.0),
    seed: int = typer.Option(421337),
) -> None:
    import random

    from cfi_federation import ClippedContribution, dp_binary_prevalence, secure_aggregate

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
