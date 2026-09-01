# Release Gate Checklist (Appendix C)

All 12 items are machine-checked in `cfi_contributor.release_gate.ReleaseGate`.

1. Local immutable evidence preserved
2. Expected outcome supported
3. Counterfactual interventions safe and repeated
4. Graph elements justified
5. Exact identifiers removed
6. Source inference assessed
7. Reconstruction attack assessed
8. No executable exploit / unpatched vuln disclosure
9. Negative controls sufficient
10. Legal/privacy/security/domain review
11. Disclosure tier and expiration explicit
12. Schema, compiler, digest, attestations, signature present

Outcomes: `reject`, `require_further_generalization`, `restrict_distribution`, `non_shareable`, `approve`.

Residual risk is a calibrated score, not a boolean "de-identified".
