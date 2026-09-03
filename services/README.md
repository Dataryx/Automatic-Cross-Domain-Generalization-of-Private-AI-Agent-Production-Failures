# Services

FastAPI/uvicorn processes started by Docker Compose or Helm.

## Core

| Directory | Port | Notes |
|-----------|------|-------|
| `registry/` | 8000 | SQLite or Postgres, review queue, audit API |
| `coordinator/` | 8001 | Consortium round coordination |
| `aggregator/` | 8002 | Secret-share aggregation, `/accountant` |

Shared helpers: `replay_common.py` (replay integration apps).

## Integrations (`integrations/`)

Local substitutes for vendor replay endpoints. Used in dev and CI when `CFI_HOOK_MODE=live` or replay profiles point at compose DNS names.

| Directory | Compose service name | Port |
|-----------|---------------------|------|
| `replay/` | `replay_mock` | 8010 |
| `agentrx/` | `agentrx_stub` | 8020 |
| `causalflow/` | `causalflow_stub` | 8021 |
| `tau/` | `tau_stub` | 8022 |

Replace these with real endpoints in production; see `docs/production-integration.md`.

## Entry style

Most services use a `main.py` with `if __name__ == "__main__"` for `python services/.../main.py`. Coordinator uses uvicorn module path: `uvicorn services.coordinator.main:app`.
