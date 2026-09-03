# Production integration guide

Wire CFI-Fed to your organization's agent runtimes and private incident corpora.

## 1. Copy environment template

```bash
cp config/production.env.example config/production.env
# Edit URLs and secrets — never commit production.env
```

## 2. Live AgentRx / CausalFlow hooks

Point at your sandboxed diagnostic endpoints (not raw production traces):

```bash
set -a && source config/production.env && set +a
cfi-contribute probe-hooks --live
python scripts/ci/verify_live_hooks.py
```

Required when `CFI_HOOK_MODE=live`:

| Variable | Example |
|----------|---------|
| `CFI_AGENTRX_URL` | `https://agentrx.internal/v1/replay` |
| `CFI_CAUSALFLOW_URL` | `https://causalflow.internal/v1/counterfactual` |

## 3. Private tenant corpus

Materialize tenant subdirectories (local only, no egress):

```bash
python scripts/ops/materialize_tenant_corpus.py --tenants 10 --clean
cfi-contribute ingest-corpus \
  --input-dir tools/evaluation/benchmarks/corpus/tenants \
  --output-dir /data/out/ingest \
  --extract --recursive
cfi-contribute ingest-publish \
  --input-dir tools/evaluation/benchmarks/corpus/tenants \
  --output-dir /data/out/publish \
  --registry-url "$CFI_REGISTRY_URL" \
  --replay-profile agentrx
```

Replace `tools/evaluation/benchmarks/corpus/tenants` with your private bundle root.

## 4. Local Kubernetes (kind)

Requires Docker Desktop running:

```bash
python scripts/ops/deploy_helm_local.py
kubectl -n cfi-fed port-forward svc/cfi-registry 8000:8000
curl http://127.0.0.1:8000/health
```

## 5. Full pipeline verification

```bash
# All 7 compose variants (Docker required):
CFI_REQUIRE_DOCKER=1 python scripts/ci/verify_pipeline_matrix_ci.py

# Remote against running stack:
cfi-contribute run-pipeline --output pipeline_summary.json
```

## Honesty

- Causal extraction from production traces is not solved.
- Structural corpus collapse may dedupe multiple incidents to one CFI id.
- kind/local deploy is a smoke test, not production hardening.
