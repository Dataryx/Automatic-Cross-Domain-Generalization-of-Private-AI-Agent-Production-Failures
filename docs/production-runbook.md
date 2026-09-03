# Production runbook (research prototype)

Operator guide for deploying CFI-Fed beyond local smoke tests. This does **not** constitute a hardened production certification.

## Pre-deploy checklist

1. PostgreSQL for registry (`CFI_DATABASE_URL=postgresql://...`).
2. TLS termination at ingress or load balancer.
3. Bearer tokens for mutating APIs (`CFI_API_TOKEN`).
4. Privacy budget configured (`CFI_TOTAL_EPSILON`, `CFI_MINIMUM_COHORT_K`).
5. External audit sink (`CFI_AUDIT_SINK_URL` or `CFI_AUDIT_SINK_PATH`).
6. Human review workflow enabled before lifecycle `active`.
7. Re-run `python tools/evaluation/verify_dod.py` after deploy.

## Path layout (compose nginx and Helm ingress)

Federation services are exposed under path prefixes that match across environments:

| Service | Path prefix | Example health |
|---------|-------------|----------------|
| Registry | `/registry` | `GET /registry/health` |
| Coordinator | `/coordinator` | `GET /coordinator/health` |
| Aggregator | `/aggregator` | `GET /aggregator/health` |
| Replay mock | `/replay` | via TLS gateway compose |
| AgentRx hook | `/agentrx` | `CFI_AGENTRX_URL=.../v1/replay` |
| CausalFlow hook | `/causalflow` | `CFI_CAUSALFLOW_URL=.../v1/counterfactual` |

Helm chart (`deploy/helm/cfi-fed/`) sets `CFI_REGISTRY_URL`, `CFI_COORDINATOR_URL`, and `CFI_AGGREGATOR_URL` to ingress paths when `ingress.enabled=true`.

```bash
helm install cfi-fed deploy/helm/cfi-fed \
  --namespace cfi-fed --create-namespace \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi' \
  --set ingress.enabled=true \
  --set ingress.tls=true \
  --set ingress.host=cfi-fed.example.com
```

## Helm replay hook services

Enable in-cluster replay stubs (AgentRx, CausalFlow, mock, tau):

```bash
helm install cfi-fed deploy/helm/cfi-fed \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi' \
  --set ingress.enabled=true \
  --set replayHooks.enabled=true
```

Validate render + kubectl dry-run locally:

```bash
python scripts/ci/verify_helm_deploy.py
```

## Multi-tenant corpus batch

```bash
python scripts/ci/verify_corpus_batch.py
# or manually materialize tenants then ingest-publish:
python -c "from corpus_tenants import materialize_tenant_corpus; from pathlib import Path; materialize_tenant_corpus(Path('tools/evaluation/benchmarks/corpus/bundles'), Path('/data/tenants'), tenant_count=10)"
```


Default stubs run on ports 8020/8021. For production agent runtimes:

```bash
export CFI_HOOK_MODE=live
export CFI_AGENTRX_URL=https://agentrx.internal/v1/replay
export CFI_CAUSALFLOW_URL=https://causalflow.internal/v1/counterfactual
cfi-contribute probe-hooks --live
```

`CFI_HOOK_MODE=live` fails closed if production URLs are unset. Causal identification is **not** guaranteed even with live endpoints.

## Private corpus ingest at scale

Incident bundles never leave the contributor zone. For tenant subdirectories:

```bash
cfi-contribute ingest-corpus \
  --input-dir /data/incidents/tenant-a \
  --output-dir /data/out/tenant-a \
  --extract \
  --recursive \
  --replay-profile agentrx

# Batch smoke (first N bundles only):
cfi-contribute ingest-corpus \
  --input-dir /data/incidents \
  --output-dir /data/out/smoke \
  --extract \
  --max-bundles 100

# Extract and publish to registry:
cfi-contribute ingest-publish \
  --input-dir /data/incidents \
  --output-dir /data/out \
  --registry-url https://cfi-fed.example.com/registry \
  --replay-profile agentrx
```

## Full pipeline verification

```bash
# In-process (no Docker):
python scripts/ci/verify_full_pipeline.py

# All 7 deployment variants (requires Docker):
CFI_REQUIRE_DOCKER=1 python scripts/ci/verify_pipeline_matrix_ci.py

# Remote against running stack:
export CFI_REGISTRY_URL=https://cfi-fed.example.com/registry
export CFI_COORDINATOR_URL=https://cfi-fed.example.com/coordinator
export CFI_AGGREGATOR_URL=https://cfi-fed.example.com/aggregator
cfi-contribute run-pipeline --output pipeline_summary.json
```

Pipeline summaries include `zk_attestation_verified` (deterministic circuit only) and `audit_export_ok`.

## ZK attestation

Federation aggregate requests include optional ZK attestation over clipped counts. This proves execution of a fixed deterministic circuit only — **not** stochastic agent evaluation fidelity.

## Monitoring

| Endpoint | Purpose |
|----------|---------|
| `GET /metrics` | Prometheus gauges |
| `GET /accountant` | Privacy budget snapshot |
| `GET /audit/export` | Governance audit trail |
| `POST /audit/sink` | Flush audit to external sink |

## Honesty guardrails

See `docs/limitations.md`. Do not claim automatic causal extraction, canonicalization confidentiality, or production attestation from this prototype.
