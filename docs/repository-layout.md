# Repository layout

How the tree is organized and where to look first.

## Applications

| Path | Role |
|------|------|
| `apps/console/` | React ops console. Talks to registry/coordinator/aggregator via Vite proxy in dev. |

## Libraries (`packages/`)

Installable Python packages. Each has `src/<name>/` and is wired into the root `pyproject.toml`.

| Package | Responsibility |
|---------|----------------|
| `cfi_core` | Schemas, signing, HTTP/TLS helpers, middleware |
| `cfi_contributor` | Incident → CFI pipeline, replay, release gate |
| `cfi_registry` | Persistence, review queue, audit export |
| `cfi_recipient` | Fetch, compile, assess, federation shares |
| `cfi_federation` | Coordinator/aggregator clients, DP accountant |
| `cfi_governance` | Audit sinks, review workflow, attestations |
| `cfi_cli` | Typer entrypoints (`cfi-contribute`, `cfi-registry`, …) |

## Services (`services/`)

Container entrypoints. Production paths:

- `registry/` — CFI catalog, review, audit (`:8000`)
- `coordinator/` — consortium rounds (`:8001`)
- `aggregator/` — clipped share aggregation, DP accountant (`:8002`)

`integrations/` holds **development-only** HTTP backends that mimic external replay systems (AgentRx, CausalFlow, τ-bench). Compose keeps the old service names (`agentrx_stub`, etc.) for stable DNS; only filesystem paths changed.

## Tools

| Path | Role |
|------|------|
| `tools/evaluation/` | Benchmarks, red-team harness, consortium/field pilots, pipeline matrix, `verify_dod.py` |
| `tools/feasibility/` | Offline seeded study for the paper — not a runtime dependency |

Python imports from evaluation code assume `tools/evaluation` is on `PYTHONPATH` (set in `pyproject.toml`).

## Scripts

| Path | Role |
|------|------|
| `scripts/ci/` | Checks invoked from CI or `make` (pipelines, compose smokes, helm validation) |
| `scripts/ops/` | Day-two ops: certs, release tarball, health probe, golden path, corpus materialization |

Naming convention: `verify_*` lives under `ci/`; everything else operational under `ops/`.

## Deploy

- `deploy/helm/cfi-fed/` — Helm chart
- `deploy/nginx/` — TLS/mTLS gateway configs used by compose overlays
- `deploy/k8s/` — Raw manifests (optional)

## Schemas

Versioned JSON under `schemas/` — CFI, incident bundle, measurement spec, cohort manifest, share envelope.

## Tests

`tests/unit`, `tests/integration`, `tests/property`, `tests/adversarial` — pytest only. Integration checks that need Docker live in `scripts/ci/`, not here.
