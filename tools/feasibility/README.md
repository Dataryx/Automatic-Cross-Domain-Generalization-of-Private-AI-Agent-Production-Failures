# Controlled feasibility study

Fixed seed **421337**. Offline only.

```bash
python tools/feasibility/run_cfi_sim.py
```

Writes CSVs and figures to `tools/feasibility/output/`.

## Scope

This exercises representation choices and protocol wiring with templated incidents. It does **not** show that we can infer a correct causal invariant from raw, noisy production telemetry.

For runtime validation use `tools/evaluation/` and `scripts/ci/`.
