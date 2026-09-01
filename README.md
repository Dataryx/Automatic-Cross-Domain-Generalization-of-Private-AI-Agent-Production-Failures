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
