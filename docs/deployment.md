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

## Production checklist

1. Run registry with PostgreSQL (`CFI_DATABASE_URL=postgresql://...`).
2. Restrict registry/coordinator network access; no raw incident ingress.
3. Configure TLS termination at load balancer.
4. Wire `HttpAgentReplayProvider` to sandboxed agent runtime (`--replay-url`).
5. Require human review via `/review/ui` before lifecycle `active`.
6. Monitor privacy accountant `remaining_epsilon` on aggregator.
7. Re-run `python eval/verify_dod.py` after deploy.

## Honesty guardrails

- Causal extraction from production traces is not solved.
- Canonicalization is not a confidentiality proof.
- DP protects tenant influence on aggregates, not poorly generalized CFIs.
- Synthetic benchmarks (`sim/`, `eval/benchmarks/`) are protocol smoke tests only.
