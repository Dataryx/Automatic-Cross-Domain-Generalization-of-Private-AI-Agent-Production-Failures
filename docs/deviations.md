# Known Paper Deviations (Appendix G)

## G1 — Edge vocabulary

- `must_precede` → directed `precedes` with `status: required_but_absent`
- `supports` → namespaced `core.ext/supports`

## G2 — Absence contributes

Represented as edge attribute `status: required_but_absent` on `precedes`/`requires`; rendered dashed.

## G3 — Disclosure tier

Canonical enum value: `member-only` (not `member`).

## G4 — Required roles

`required_mapping_roles` computed from schema; `Outcome` derived → **r = 6** for exception-precedence example.

## G5 — Below-chance attribution

0.073 vs 1/8 chance is a corpus/classifier diagnostic, **not** a privacy guarantee.

## G6 — η, δ, λ

Required configuration in `MinimizationConfig` with no defaults.

## G7 — Minimum cohort k

Configurable; consortium gate defaults to **10**.
