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
- [Known deviations from paper](docs/deviations.md)

## Schemas (`schemas/`)

- `cfi/1.0` — Causal Failure Invariant
- `incident-bundle/1.0` — local contributor incident (never egress)
- `measurement-spec/1.0` — signed measurement specification
- `cohort-manifest/1.0` — frozen cohort configuration
- `share-envelope/1.0` — clipped secret-share wire format

## Recent additions

- PostgreSQL/SQLite registry persistence (`cfi_registry.db`)
- Lifecycle API: `GET/POST /cfi/{id}/lifecycle`
- Contributor pipeline (`cfi_contributor.pipeline`) + replay provider
- Federation protocol helpers (`cfi_federation.protocol`)
- Optional ZK attestation for deterministic circuits (`cfi_federation.zk_attestation`)
- Phase 4 e2e integration tests (34 passing)
- Mitigation loop with regression promotion (`cfi_recipient.mitigation`)
- Separate metric families reporter (`cfi_recipient.metrics`)

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CFI_DATABASE_URL` | `sqlite:///./cfi_registry.db` | Registry persistence |
| `CFI_MINIMUM_COHORT_K` | `10` | Consortium release threshold |
| `CFI_TOTAL_EPSILON` | `10.0` | Privacy budget for aggregator |
