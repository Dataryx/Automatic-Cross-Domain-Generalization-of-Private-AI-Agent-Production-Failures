# Helm chart (research prototype)

Parameterized chart wrapping the flat K8s manifests in `deploy/k8s/`.

```bash
docker build -t cfi-fed:latest .

helm install cfi-fed deploy/helm/cfi-fed \
  --namespace cfi-fed --create-namespace \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi' \
  --set audit.sinkSigned=1 \
  --set audit.sinkWorm=1 \
  --set audit.sinkIdempotency=1

# Dry-run render
helm template cfi-fed deploy/helm/cfi-fed \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi'
```

## Values

| Key | Purpose |
|-----|---------|
| `registry.databaseUrl` | Postgres URL (required) |
| `audit.sinkSigned` | `CFI_AUDIT_SINK_SIGNED` |
| `audit.sinkWorm` | `CFI_AUDIT_SINK_WORM` |
| `audit.sinkIdempotency` | `CFI_AUDIT_SINK_IDEMPOTENCY` |
| `ingress.enabled` | Expose registry/coordinator/aggregator |

## Honesty

Helm packaging does not constitute production hardening. TLS termination, secrets rotation, and WORM storage remain operator responsibilities.
