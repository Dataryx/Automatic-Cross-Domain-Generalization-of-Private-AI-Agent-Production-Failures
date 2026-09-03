# CFI-Fed Operations Dashboard

Professional React operations console for the CFI-Fed federation prototype.

## Features

- **Overview** — service health, registry stats, privacy budget snapshot
- **Review Queue** — human-in-the-loop CFI approval workflow
- **Privacy Budget** — differential privacy ε accountant from the aggregator
- **Audit Log** — governance events from the registry

## Prerequisites

- Node.js 18+
- CFI-Fed stack running (`docker compose up` or `make stack`)

## Development

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API calls to:

| Proxy path | Service | Port |
|------------|---------|------|
| `/api/registry` | Registry | 8000 |
| `/api/coordinator` | Coordinator | 8001 |
| `/api/aggregator` | Aggregator | 8002 |

## Production build

```bash
npm run build
npm run preview   # serves dist/ on :4173
```

From the repo root:

```bash
make dashboard-build
make dashboard-dev
```

## CORS

Registry, coordinator, and aggregator enable CORS for `http://localhost:5173` by default (`CFI_CORS_ORIGINS`). Set comma-separated origins when serving the dashboard from another host.
