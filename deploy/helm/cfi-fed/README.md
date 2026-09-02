CFI-Fed Helm chart (research prototype)

Parameterized chart wrapping the flat K8s manifests in `deploy/k8s/`.

```bash
docker build -t cfi-fed:latest .

helm install cfi-fed deploy/helm/cfi-fed \
  --namespace cfi-fed --create-namespace \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi' \
  --set ingress.enabled=true \
  --set ingress.tls=true \
  --set audit.sinkSigned=1

# Dry-run render
helm template cfi-fed deploy/helm/cfi-fed \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi' \
  --set ingress.enabled=true
```

## Ingress paths

When `ingress.enabled=true`, federation URLs use path prefixes aligned with compose nginx:

- `https://<host>/registry`
- `https://<host>/coordinator`
- `https://<host>/aggregator`

`ingress.rewrite=true` (default) strips prefixes before forwarding to backend services.

## Values

| Key | Purpose |
|-----|---------|
| `registry.databaseUrl` | Postgres URL (required) |
| `ingress.enabled` | Expose registry/coordinator/aggregator |
| `ingress.rewrite` | nginx rewrite-target for path prefixes |
| `client.agentrxUrl` | `CFI_AGENTRX_URL` for live hooks |
| `client.causalflowUrl` | `CFI_CAUSALFLOW_URL` for live hooks |
| `audit.sinkSigned` | `CFI_AUDIT_SINK_SIGNED` |

See `docs/production-runbook.md` for operator steps.

## Honesty

Helm packaging does not constitute production hardening. TLS termination, secrets rotation, and WORM storage remain operator responsibilities.
