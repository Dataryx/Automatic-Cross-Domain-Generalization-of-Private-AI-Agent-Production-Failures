# CFI-Fed Architecture

## Trust zones

```mermaid
flowchart LR
    subgraph Contributor["Contributor tenant"]
        RAW[Raw traces & policies]
        EXTRACT[Extraction pipeline]
        GATE[Release gate]
        PKG[Packager]
        RAW --> EXTRACT --> GATE --> PKG
    end
    subgraph Registry["Registry / coordinator"]
        CFI_STORE[Signed CFIs]
        COHORT[Cohort manifests]
    end
    subgraph Recipient["Recipient tenant"]
        COMP[Compiler]
        SBX[Sandbox evaluator]
        COMP --> SBX
    end
    subgraph Agg["Aggregation service"]
        SA[Secure aggregation + DP]
    end
    PKG -->|signed CFI only| CFI_STORE
    CFI_STORE --> COMP
    SBX -->|clipped shares| SA
    COHORT --> COMP
    SA -->|noisy aggregate| Recipient
```

## Requirements traceability

| Module | R1–R8 |
|--------|-------|
| `cfi_contributor` | R1, R3 |
| `cfi_core.canonicalize` | R2 (not R3 proof) |
| `cfi_recipient.compiler` | R2, R4, R6 |
| `cfi_recipient.sandbox` | R4, R5 |
| `cfi_federation` | R4, R7 |
| `cfi_governance` | R8 |
| `cfi_registry` | R8 |

## Honesty guardrails

Every API response that includes a rate or privacy metric must include `assumptions`,
`measurement_spec_id`, and `cohort_id` where applicable.
