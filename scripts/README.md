# Scripts

Two buckets — don't mix them up.

## `ci/`

Automated gates. Safe to run in CI and on every PR:

- Pipeline smokes (`verify_*_full_pipeline.py`)
- Compose / Postgres / TLS / mTLS matrix
- Helm chart render, deploy dry-run
- Feature-specific checks (agent hooks, corpus batch, audit attestation, …)

Invoked via `make` targets and `.github/workflows/ci.yml`.

## `ops/`

Things an operator runs by hand:

| Script | Purpose |
|--------|---------|
| `generate_dev_certs.py` | TLS material for local compose overlays |
| `deploy_helm_local.py` | kind cluster + chart install |
| `package_release.py` / `verify_release.py` | Release tarball + signature |
| `health_check.py` | In-process health sweep (no Docker) |
| `golden_path.py` | Cross-domain golden scenario |
| `live_replay_smoke.py` | Replay profile HTTP probe |
| `materialize_tenant_corpus.py` | Generate tenant benchmark bundles |

All scripts resolve repo root as `Path(__file__).resolve().parents[2]` (they live one level down from the old `scripts/` root).
