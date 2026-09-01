# Controlled Feasibility Study

Fixed seed **421337**. Representation and protocol smoke test only.

```bash
python sim/run_cfi_sim.py
```

Outputs land in `sim/output/` (CSVs, figures PDF+PNG).

## Honest framing

This study does **not** evaluate extracting a correct causal invariant from raw production traces.
It uses templated incidents with supplied graph features.

## Expected results (§9)

See `sim/output/q1_lodo_summary.csv` and companion tables after each run.
