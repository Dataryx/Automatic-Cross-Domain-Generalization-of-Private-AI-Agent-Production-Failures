# Deployment guide

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
make test
make golden                     # end-to-end smoke (in-process)
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Registry | 8000 | Signed CFI storage, review queue |
| Coordinator | 8001 | Cohort epochs, consortium rounds |
| Aggregator | 8002 | DP secure aggregation |
| Replay mock | 8010 | HTTP agent replay stub |
| AgentRx stub | 8020 | Sandboxed AgentRx diagnostic hook |
| CausalFlow stub | 8021 | Sandboxed counterfactual replay hook |
| τ-bench stub | 8022 | Task-format stub for live τ adapter smoke |

```bash
docker compose up --build
# End-to-end stack smoke (requires running Docker daemon):
CFI_REQUIRE_DOCKER=1 python scripts/verify_compose_stack.py
# Full pipeline against live compose services (publish -> assess -> federate -> consortium):
CFI_REQUIRE_DOCKER=1 python scripts/verify_compose_full_pipeline.py
# Postgres-backed registry:
docker compose -f docker-compose.postgres.yml up --build
CFI_REQUIRE_DOCKER=1 python scripts/verify_postgres_compose.py
CFI_REQUIRE_DOCKER=1 python scripts/verify_postgres_compose_full_pipeline.py
# TLS-terminated stack (dev self-signed certs on :8443):
python scripts/generate_dev_certs.py
docker compose -f docker-compose.tls.yml up --build
CFI_REQUIRE_DOCKER=1 python scripts/verify_tls_full_pipeline.py
# TLS paths: /registry/, /coordinator/, /aggregator/, /replay/, /agentrx/, /causalflow/, /tau/
# mTLS-terminated stack (optional client certs):
docker compose -f docker-compose.mtls.yml up --build
CFI_REQUIRE_DOCKER=1 python scripts/verify_mtls_full_pipeline.py
# or individually:
cfi-registry serve
python services/coordinator/main.py
python services/aggregator/main.py
python services/replay_mock/main.py
python services/agentrx_stub/main.py
python services/causalflow_stub/main.py
```

## Environment variables

| Variable | Default | Notes |
|----------|---------|-------|
| `CFI_DATABASE_URL` | `sqlite:///./cfi_registry.db` | Use Postgres in production |
| `CFI_MINIMUM_COHORT_K` | `10` | Consortium release threshold |
| `CFI_TOTAL_EPSILON` | `10.0` | Aggregator privacy budget |
| `CFI_HOST` / `CFI_PORT` | per service | Bind address |
| `CFI_REPLAY_MOCK_URL` | `http://127.0.0.1:8010/replay` | Mock replay profile |
| `CFI_AGENTRX_URL` | `http://127.0.0.1:8020/v1/replay` | AgentRx sandbox endpoint |
| `CFI_CAUSALFLOW_URL` | `http://127.0.0.1:8021/v1/counterfactual` | CausalFlow sandbox endpoint |
| `CFI_REGISTRY_URL` | `http://127.0.0.1:8000` | Registry base URL for remote CLI workflows |
| `CFI_COORDINATOR_URL` | `http://127.0.0.1:8001` | Coordinator base URL |
| `CFI_AGGREGATOR_URL` | `http://127.0.0.1:8002` | Aggregator base URL |
| `CFI_TLS_GATEWAY_URL` | `https://127.0.0.1:8443` | nginx TLS gateway for path-prefixed services |
| `CFI_TLS_VERIFY` | `1` | Set `0` to disable TLS cert verification (dev self-signed only) |
| `CFI_TLS_CA_BUNDLE` | unset | Custom CA bundle path for federation HTTP clients |
| `CFI_MTLS_CLIENT_CERT` | unset | Client certificate PEM for mTLS federation clients |
| `CFI_MTLS_CLIENT_KEY` | unset | Client private key PEM for mTLS federation clients |
| `CFI_TAU_BENCH_URL` | unset | Optional τ-bench task JSON endpoint (format adapter only) |
| `CFI_RATE_LIMIT_RPM` | `0` (disabled) | Per-client requests/minute; set e.g. `120` in production |
| `CFI_API_TOKEN` | unset | Bearer token for mutating API calls; health/metrics bypass |
| `CFI_OTEL_ENDPOINT` | unset | OTLP HTTP trace exporter URL (requires `pip install -e ".[otel]"`) |
| `CFI_AUDIT_SINK_PATH` | unset | Append-only NDJSON file for governance audit export |
| `CFI_AUDIT_SINK_URL` | unset | Webhook URL for `POST /audit/sink` batch delivery |
| `CFI_AUDIT_SINK_RETRIES` | `3` | Webhook retry count with exponential backoff |
| `CFI_RELEASE_SIGNING_ORG` | `cfi-fed-release` | Org id embedded in signed release manifest |
| `CFI_RELEASE_SIGNING_KEY_PEM` | unset | Ed25519 private key PEM for stable release signatures |
| `CFI_RELEASE_SIGNING_KEY_PATH` | unset | Path to Ed25519 private key PEM (alternative to inline PEM) |
| `CFI_AUDIT_SINK_WATERMARK_PATH` | unset | Persist audit sink cursor across restarts |
| `CFI_AUDIT_SIGNING_KEY_PEM` | unset | Ed25519 key for signed audit exports |
| `CFI_AUDIT_SIGNING_KEY_PATH` | unset | Path to audit signing key PEM |
| `CFI_AUDIT_SINK_SIGNED` | `0` | Emit signed batch on `POST /audit/sink` |
| `CFI_AUDIT_SINK_WORM` | `0` | Append-only hash chain wrapper on file sink |
| `CFI_AUDIT_SINK_IDEMPOTENCY` | `0` | Skip duplicate batch ids (SIEM replay protection) |
| `CFI_AUDIT_SINK_IDEMPOTENCY_PATH` | unset | Persist flushed batch id ledger |

```bash
cfi-contribute replay-profiles
cfi-contribute endpoints
cfi-contribute run-pipeline --output pipeline_summary.json
cfi-contribute probe-hooks
cfi-contribute probe-hooks --profile agentrx
cfi-contribute extract --output cfi.json --replay-profile mock
cfi-contribute extract --output cfi.json --replay-url http://127.0.0.1:8010/replay
cfi-contribute register --package-path cfi.json --registry-url http://127.0.0.1:8000
cfi-contribute publish --output cfi.json --registry-url http://127.0.0.1:8000
cfi-contribute status --invariant-id CFI-EXCEPTION-PRECEDENCE-0001
cfi-recipient fetch --invariant-id CFI-EXCEPTION-PRECEDENCE-0001 --output fetched.json
cfi-recipient pull --invariant-id CFI-EXCEPTION-PRECEDENCE-0001 --domain procurement
cfi-recipient assess --invariant-id CFI-EXCEPTION-PRECEDENCE-0001 --domain procurement --output assess.json
cfi-recipient contribute --invariant-id CFI-EXCEPTION-PRECEDENCE-0001 --tenant-id tenant-a --envelope-output envelope.json
cfi-aggregate round --coordinator-url http://127.0.0.1:8001 --tenants 12 --minimum-k 10
```

## Production checklist

1. Run registry with PostgreSQL (`CFI_DATABASE_URL=postgresql://...`).
2. Lifecycle state and review tickets persist in `artifact_lifecycle` and `review_tickets` tables.
2. Restrict registry/coordinator network access; no raw incident ingress.
3. Configure TLS termination at load balancer.
4. Wire `HttpAgentReplayProvider` to sandboxed agent runtime (`--replay-url`).
5. Require human review via `/review/ui` before lifecycle `active`.
6. Monitor privacy accountant `remaining_epsilon` on aggregator (`GET /accountant`, `GET /metrics`).
7. Re-run `python eval/verify_dod.py` after deploy.
8. Ingest private incident bundles locally: `cfi-contribute ingest-corpus --input-dir ./bundles --output-dir ./out --extract
cfi-contribute ingest-publish --input-dir ./bundles --output-dir ./out --registry-url http://127.0.0.1:8000`.
9. Configure external audit sink (`CFI_AUDIT_SINK_PATH` or `CFI_AUDIT_SINK_URL`) and flush via `POST /audit/sink`.
10. Build signed release checkpoint: `make verify-release` (writes `eval/output/release_manifest.json`).
11. For reproducible release signatures: `python scripts/generate_release_signing_key.py` then set `CFI_RELEASE_SIGNING_KEY_PATH`.
12. Kubernetes (prototype): flat manifests `deploy/k8s/cfi-fed.yaml` or Helm chart `deploy/helm/cfi-fed/`.

## Observability

| Endpoint | Service | Purpose |
|----------|---------|---------|
| `GET /health` | all | Liveness |
| `GET /ready` | registry, coordinator, aggregator | Readiness |
| `GET /metrics` | all | Prometheus text gauges |
| `GET /accountant` | aggregator | Privacy budget JSON snapshot |
| `GET /audit/export` | registry | In-memory governance audit trail |
| `GET /audit/status` | registry | Audit cursor, pending export count |
| `GET /audit/export/signed` | registry | Ed25519-signed audit batch |
| `POST /audit/sink` | registry | Flush audit events to external sink |

```bash
python scripts/verify_observability.py
make health
python scripts/verify_production_hardening.py
python scripts/verify_auth.py
make verify-release
```

## Honesty guardrails

- Causal extraction from production traces is not solved.
- Canonicalization is not a confidentiality proof.
- DP protects tenant influence on aggregates, not poorly generalized CFIs.
- Synthetic benchmarks (`sim/`, `eval/benchmarks/`) are protocol smoke tests only.
