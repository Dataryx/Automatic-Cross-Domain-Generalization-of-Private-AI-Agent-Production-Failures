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

```bash
docker compose up --build
# Postgres-backed registry:
docker compose -f docker-compose.postgres.yml up --build
# TLS-terminated stack (dev self-signed certs on :8443):
python scripts/generate_dev_certs.py
docker compose -f docker-compose.tls.yml up --build
# or individually:
cfi-registry serve
python services/coordinator/main.py
python services/aggregator/main.py
python services/replay_mock/main.py
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

```bash
cfi-contribute replay-profiles
cfi-contribute extract --output cfi.json --replay-profile mock
cfi-contribute extract --output cfi.json --replay-url http://127.0.0.1:8010/replay
```

## Production checklist

1. Run registry with PostgreSQL (`CFI_DATABASE_URL=postgresql://...`).
2. Restrict registry/coordinator network access; no raw incident ingress.
3. Configure TLS termination at load balancer.
4. Wire `HttpAgentReplayProvider` to sandboxed agent runtime (`--replay-url`).
5. Require human review via `/review/ui` before lifecycle `active`.
6. Monitor privacy accountant `remaining_epsilon` on aggregator.
7. Re-run `python eval/verify_dod.py` after deploy.
8. Ingest private incident bundles locally: `cfi-contribute ingest-corpus --input-dir ./bundles --output-dir ./out --extract`.

## Honesty guardrails

- Causal extraction from production traces is not solved.
- Canonicalization is not a confidentiality proof.
- DP protects tenant influence on aggregates, not poorly generalized CFIs.
- Synthetic benchmarks (`sim/`, `eval/benchmarks/`) are protocol smoke tests only.
