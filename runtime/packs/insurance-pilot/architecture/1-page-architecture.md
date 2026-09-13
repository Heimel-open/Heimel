# One-page architecture — valo-insurance-pilot

## The chain

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ INSURANCE LAYER (evaluates + attests; NEVER authorizes execution)            │
│                                                                             │
│  AssuranceProfileV1  ──►  CommitAssuranceEvaluationV1                        │
│   (coverage condition)     capability-set subsumption, fail-closed          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ evidence + verdict
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION CHAIN (the only path consequence can take)                         │
│                                                                             │
│  reht ──► RACS ──► Gateway/PEP ──► external effect ──► Veritas               │
│  sole    signed clearance   consumes one-shot     receipt   write-once       │
│  ALLOW   verification       permit; binds action  digest    attestation log  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAIMS EVIDENCE (deterministic, offline-verifiable)                          │
│                                                                             │
│  ClaimsEvidencePackV1 ── binds ── profile + action + evaluation +            │
│                                   reht + racs + receipt + veritas + policy   │
│  ──► verify offline in isolation (no runtime access needed)                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Roles (non-negotiable)

| Component | Role | Never |
|---|---|---|
| AssuranceProfileV1 | Carrier coverage condition, machine-readable | grants authority |
| CommitAssuranceEvaluationV1 | Commit-time verdict; fail-closed | issues permits |
| reht | Sole authorization boundary (ALLOW/DENY) | overridden by insurance |
| RACS | Action-control standard; signed clearance | creates authority |
| Gateway/PEP | Execution enforcement; one-shot permit | mints authority |
| Veritas | Write-once receipt attestation | overwritten |
| ClaimsEvidencePackV1 | Deterministic why-happened evidence | tampered |

## The three load-bearing ideas

1. **Fail-closed absence.** Missing observability is `UNKNOWN`, never presumed
   `ACTIVE`/`UNCHANGED`.
2. **Capability semantics.** Assurance strength is a capability set
   (`required_capabilities ⊆ actual_capabilities`), not a linear ranking.
3. **Non-authority of insurance.** The insurer can underwrite and settle from
   machine evidence without ever being able to execute an action.

## What the carrier receives

- A coverage condition as a machine profile (`AssuranceProfileV1`).
- A sample `ClaimsEvidencePackV1` it can verify offline today.
- The same artifacts in the shadow pilot against one real enterprise workflow
  before any premium/coverage effect is discussed.
