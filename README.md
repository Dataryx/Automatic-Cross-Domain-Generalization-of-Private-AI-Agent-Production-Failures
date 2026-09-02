# CFI-Fed

Privacy-preserving architecture that converts one organization's private AI-agent production
incident into a minimal, domain-neutral **Causal Failure Invariant (CFI)** that unrelated
organizations compile — entirely inside their own trust boundary — into structurally equivalent
but semantically different tests.

## Research honesty

This system does **not** claim that:

- automatic causal extraction from raw production traces is solved;
- canonicalization alone guarantees confidentiality;
- differential privacy does **not** protect the source incident.

Every surface that reports a privacy or causality result carries its assumptions, cohort, and
measurement specification.

## Trust boundaries

| Zone | Holds | Emits |
|------|-------|-------|
| Contributor | Raw traces, policies, identities | Signed, reviewed CFI only |
| Registry / coordinator | CFIs, signatures, cohort metadata | Signed manifests |
| Recipient | Ontology, mappings, cases, outcomes | Clipped secret shares only |
| Aggregation | Secret shares | Thresholded DP aggregate |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Controlled feasibility study (seed 421337, no network)
python sim/run_cfi_sim.py

# Run tests
pytest tests/ -q

# Golden cross-domain example
pytest tests/integration/test_retail_cross_domain.py -v
```

## Controlled study (`sim/`)

The feasibility study is a **representation and protocol smoke test**. It does **not** evaluate
extracting a correct causal invariant from raw, noisy, real production traces, and uses no live
agents, confidential incidents, or human experts.

Re-running `sim/run_cfi_sim.py` recreates all CSVs and figures from fixed seed 421337.

## Commercial deployment path

1. On-premises incident compiler (local regression families)
2. Cross-domain assurance library (signed invariants, local compilation)
3. Private consortium (secure aggregation)
4. Neutral network (registry, cohort statistics)

## Documentation

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat_model.md)
- [Governance](docs/governance.md)
- [Release gate checklist](docs/release_gate_checklist.md)
- [Limitations](docs/limitations.md)
- [Deployment](docs/deployment.md)
- [Known deviations from paper](docs/deviations.md)

## Schemas (`schemas/`)

- `cfi/1.0` — Causal Failure Invariant
- `incident-bundle/1.0` — local contributor incident (never egress)
- `measurement-spec/1.0` — signed measurement specification
- `cohort-manifest/1.0` — frozen cohort configuration
- `share-envelope/1.0` — clipped secret-share wire format

## Recent additions

- Phase 5: consortium coordinator (`cfi_federation.consortium`) + `cfi-aggregate consortium`
- Phase 6: prospective field-study harness (`eval/field/`) + `cfi-recipient mitigate`
- Phase 7: CI + Docker Compose + production ablation baselines
- Phase 8: human review queue (`GET /review/ui`), trained attribution model, HTTP replay adapter, benchmark corpus
- Phase 9: computed production baselines, replay mock service (`:8010`), `--replay-url` on extract
- Phase 10: golden-path smoke (`scripts/golden_path.py`), τ-adapter, coordinator consortium API, `Makefile`
- Phase 11: JCS stability tests, registry audit API, `cfi-contribute gate`, sim CI job
- Phase 12: Postgres compose, supersession API, sandbox egress tests, `cfi-recipient evaluate`, health check
- Phase 13: mypy CI, enhanced review UI + ticket API, live replay smoke (`scripts/live_replay_smoke.py`)
- Phase 14: replay profiles (`mock`/`agentrx`/`causalflow`), figure + field-study verification in CI
- Phase 15: private corpus ingestion (`cfi-contribute ingest-corpus`), TLS compose (`docker-compose.tls.yml`)
- Phase 16: observability (`/health`, `/ready`, `/metrics`, `/accountant`) + privacy budget monitoring
- Phase 17: request tracing (`X-Request-ID`), optional rate limiting (`CFI_RATE_LIMIT_RPM`), production middleware
- Phase 18: bearer API auth (`CFI_API_TOKEN`), OTLP tracing (`CFI_OTEL_ENDPOINT`), `GET /tracing` status
- Phase 19: governance audit export (`GET /audit/export`), mTLS compose, release packaging (`scripts/package_release.py`)
- Phase 20: signed release attestation, external audit sink (`POST /audit/sink`, `CFI_AUDIT_SINK_PATH` / `CFI_AUDIT_SINK_URL`), `scripts/verify_release.py`
- Phase 21: Postgres `audit_events` table, webhook retry (`CFI_AUDIT_SINK_RETRIES`), stable release signing key, CI release job
- Phase 22: AgentRx/CausalFlow replay stubs (`:8020`/`:8021`), audit sink watermark dedup, `scripts/verify_replay_profiles.py`
- Release-gate adversaries auto-scored in `ReleaseGate.run()`
- CI workflow (`.github/workflows/ci.yml`) + `docker-compose.yml` for services
- `eval/run_all.py` — runs pytest, DoD checks, and all pilots
- PostgreSQL/SQLite registry persistence (`cfi_registry.db`)
- Lifecycle API: `GET/POST /cfi/{id}/lifecycle`
- Contributor pipeline (`cfi_contributor.pipeline`) + replay provider
- Federation protocol helpers (`cfi_federation.protocol`)
- Optional ZK attestation for deterministic circuits (`cfi_federation.zk_attestation`)
- Mitigation loop with regression promotion (`cfi_recipient.mitigation`)
- Separate metric families reporter (`cfi_recipient.metrics`)

## Evaluation harnesses

```bash
python eval/run_all.py              # full suite
python eval/verify_dod.py           # Section 15 checks
python eval/consortium/run_consortium_pilot.py
python eval/field/run_prospective_pilot.py
python eval/production/harness.py
python eval/benchmarks/run_corpus.py
```

## Human review

Registry exposes a minimal review queue after CFI registration:

```bash
cfi-registry serve
# open http://127.0.0.1:8000/review/ui
```

## Docker

```bash
docker compose up --build
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CFI_DATABASE_URL` | `sqlite:///./cfi_registry.db` | Registry persistence |
| `CFI_MINIMUM_COHORT_K` | `10` | Consortium release threshold |
| `CFI_TOTAL_EPSILON` | `10.0` | Privacy budget for aggregator |
