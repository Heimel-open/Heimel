# AGENTS.md — valo-insurance-pack

## Architecture Overview

`valo-insurance-pack` is the **insurance product layer** built over the existing REHT chain:

```text
Kernel authoritative state -> governed workspace -> worker -> fresh state + Authority State -> reht -> RACS -> PEP/Gateway -> receipt -> Veritas
```

### Core Invariants

1. **Non-authority of Insurance**: The insurance layer makes autonomous consequence-bearing actions machine-underwritable and verifiable without moving insurance logic into REHT or claiming execution authority.
2. **Strict Chain Preservation**:
   - `AssuranceProfileV1` is input to assurance evaluation; it NEVER grants execution authority.
   - REHT remains the sole authorization boundary (`ALLOW` / `DENY`).
   - RACS remains the action control standard.
   - Gateway/PEP remains the execution enforcement point.
   - Veritas remains the write-once receipt attestation log.
3. **Fail-Closed Assurance**: If required source assurance evidence is missing, stale, invalid, or revoked, the assurance evaluation fails closed according to the profile failure outcome (`DENY`, `STEP_UP`, `DEFER`, `HALT`).
4. **Policy-Binding & Claims Evidence**: Cryptographically binds policy coverage conditions, assurance profile versions, actions, REHT clearances, RACS decisions, execution receipts, and Veritas outcomes into deterministic `ClaimsEvidencePackV1` bundles verifiable without worker chain-of-thought.
5. **Pure Technical Telemetry**: Underwriting telemetry aggregates only technical assurance signals (clearance rates, step-up/defer rates, evidence freshness/revocation visibility, exposure). No premium pricing or subjective underwriting decisions are made inside VALO.
