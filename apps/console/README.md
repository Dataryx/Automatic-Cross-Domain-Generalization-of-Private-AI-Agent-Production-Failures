# Ops console

Internal UI for federation operators. Not customer-facing.

## Pages

- **Overview** — service health, registry counts, privacy budget snapshot (30s refresh)
- **Review queue** — approve / reject / send back for generalization
- **Privacy budget** — aggregator ε accountant
- **Audit log** — registry governance events (not a WORM archive)

## Run locally

Stack must be up (`make stack` or `docker compose up`).

```bash
cd apps/console
npm install
npm run dev
```

http://localhost:5173

Vite proxies `/api/registry`, `/api/coordinator`, `/api/aggregator` to ports 8000–8002.

## Build

```bash
npm run build
npm run preview    # static dist on :4173
```

From repo root: `make console-build`.

## CORS

Backends allow `http://localhost:5173` by default (`CFI_CORS_ORIGINS`). Add your host if you serve the built assets elsewhere.
