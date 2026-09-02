# Kubernetes deployment (research prototype)

Minimal manifests for registry, coordinator, and aggregator. Build the image locally first:

```bash
docker build -t cfi-fed:latest .
```

Create secrets (Postgres URL required for production registry):

```bash
kubectl create namespace cfi-fed
kubectl -n cfi-fed create secret generic cfi-fed-secrets \
  --from-literal=database_url='postgresql://user:pass@postgres:5432/cfi'
kubectl apply -f deploy/k8s/cfi-fed.yaml
```

Or install via Helm:

```bash
helm install cfi-fed deploy/helm/cfi-fed \
  --namespace cfi-fed --create-namespace \
  --set registry.databaseUrl='postgresql://user:pass@postgres:5432/cfi'
```

See `deploy/helm/cfi-fed/README.md` for values.

## Notes

- Image tag `cfi-fed:latest` is for local/dev clusters (minikube, kind). Push to your registry for production.
- Registry expects `CFI_DATABASE_URL` from secret `cfi-fed-secrets`.
- Replay stubs are not included; wire `CFI_REPLAY_MOCK_URL` at the contributor edge.
- TLS/mTLS termination should be handled by an ingress controller or service mesh.
- Signed audit exports: `GET /audit/export/signed` on the registry service.

## Honesty

These manifests demonstrate deployability only. They do not constitute a hardened production deployment.
