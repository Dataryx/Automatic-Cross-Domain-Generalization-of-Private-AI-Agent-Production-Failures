# Threat Model

## Protected assets

Source incidents, recipient mappings, per-tenant susceptibility, embargoed vulnerability data.

## Adversaries (harnesses in `tools/evaluation/redteam/`)

1. Honest-but-curious registry
2. Malicious recipient
3. Malicious contributor
4. Sybil organizations
5. Collusion (registry / aggregation / tenants)
6. External observers (timing correlation)
7. Model or tool provider (API traffic)

## Out of scope

Full endpoint compromise, malicious local administrators, hardware side channels.

## Residual risk

Canonicalization and DP reduce but do not eliminate source inference. Residual risk is measured,
not assumed zero.
