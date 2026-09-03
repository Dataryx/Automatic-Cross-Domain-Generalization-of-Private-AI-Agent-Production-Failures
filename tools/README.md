# Tools

Code that supports research and release qualification — not imported by production services at runtime.

## `evaluation/`

Benchmarks, pilots, and the Definition-of-Done gate (`verify_dod.py`).

Notable entrypoints:

```bash
python tools/evaluation/verify_dod.py
python tools/evaluation/run_all.py
python tools/evaluation/benchmarks/run_corpus.py
python tools/evaluation/production/harness.py
```

Generated artifacts land in `tools/evaluation/output/` (gitignored).

## `feasibility/`

Offline study for the paper. Seed `421337`, no network, templated incidents. Outputs in `tools/feasibility/output/`.

```bash
python tools/feasibility/run_cfi_sim.py
```

This does **not** validate causal extraction from real traces — see `tools/feasibility/README.md`.
