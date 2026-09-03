# CFI-Fed

Federation stack for sharing **Causal Failure Invariants (CFIs)** across organizations without moving raw production incidents out of the contributor boundary.

A contributor compiles a local failure into a signed, reviewed invariant. Recipients pull from the registry and compile it into their own test suites. Optional consortium aggregation adds differential privacy on clipped statistics.

This repo is a research prototype. It ships working services, CLIs, and an ops console — not a certified compliance product.

## What we do not claim

- Causal structure can be recovered automatically from noisy production traces.
- Canonicalization alone prevents re-identification.
- Differential privacy substitutes for careful generalization before release.

Every metric and privacy number in the system is labeled with its assumptions.

## Repository layout

```
apps/console/          React ops UI (review queue, health, audit)
packages/              Python libraries (cfi_core, contributor, registry, …)
services/              Long-running APIs (registry, coordinator, aggregator)
services/integrations/ Local dev backends for replay hooks (AgentRx, CausalFlow, τ)
tools/evaluation/      Benchmarks, pilots, pipeline smokes, DoD gate
tools/feasibility/     Seeded paper study (no network)
scripts/ci/            Integration checks run in CI and before releases
scripts/ops/           Certs, packaging, health probes, corpus utilities
deploy/                Helm chart, nginx TLS configs, k8s manifests
docs/                  Architecture, threat model, runbooks
schemas/               Wire-format JSON schemas (versioned)
```

See [docs/repository-layout.md](docs/repository-layout.md) for detail.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest tests/ -q
make stack                           # docker compose up
make console-dev                     # ops UI on :5173
```

Feasibility study (fixed seed, offline):

```bash
python tools/feasibility/run_cfi_sim.py
```

## Operations console

With the compose stack running:

```bash
cd apps/console
npm install
npm run dev
```

Open http://localhost:5173 — overview, review queue, privacy budget, audit log.

Legacy HTML review page still lives at http://localhost:8000/review/ui.

## Common make targets

| Target | What it does |
|--------|----------------|
| `make test` | Unit + integration pytest |
| `make dod` | Definition-of-done gate |
| `make stack` | Docker compose (all services) |
| `make full-pipeline` | Publish → assess → federate smoke |
| `make console-dev` | Vite dev server for ops UI |
| `make eval-all` | Full evaluation harness sweep |

Run `make` without arguments to list everything.

## Documentation

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat_model.md)
- [Governance](docs/governance.md)
- [Deployment](docs/deployment.md)
- [Production runbook](docs/production-runbook.md)
- [Release gate checklist](docs/release_gate_checklist.md)
- [Limitations](docs/limitations.md)

## Docker

```bash
docker compose up --build
```

Ports: registry `8000`, coordinator `8001`, aggregator `8002`, replay integrations `8010–8022`.

## Environment variables (frequently used)

| Variable | Default | Notes |
|----------|---------|-------|
| `CFI_DATABASE_URL` | `sqlite:///./cfi_registry.db` | Registry backing store |
| `CFI_MINIMUM_COHORT_K` | `10` | Minimum cohort before aggregate release |
| `CFI_TOTAL_EPSILON` | `10.0` | Consortium DP budget |
| `CFI_CORS_ORIGINS` | `http://localhost:5173` | Allowed console origins |
| `CFI_REGISTRY_URL` | — | CLI default registry base URL |

Full list in [config/production.env.example](config/production.env.example).
