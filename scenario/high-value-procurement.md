# valo-insurance-pilot — high-value procurement scenario

## Narrative

A governed enterprise agent (procurement worker) creates a high-value purchase
order against the SAP ERP: **PO-2026-7701**, **EUR 250,000**, vendor
**SUPPLIER-BETA**. This is a consequence-bearing action — money and supplier
commitment move on it.

Before any consequence happens, the agent's runtime must clear **five
sequential gates**, and the insurance layer must be able to prove all five
retrospectively:

```text
1. Identity      — the acting principal is who it claims to be (Entra, FIDO2-bound)
2. Authority     — the actor has budget + procurement capability (ERP authoritative API)
3. State         — the PO being committed exists and is committed (ERP committed state)
4. Authorization — REHT issues the only ALLOW that may execute (sole boundary)
5. Control       — RACS signs/verifies the clearance; Gateway/PEP consumes a one-shot permit; Veritas writes the receipt
```

If any gate fails — stale evidence, unknown revocation status, missing source,
capability shortfall — the action is **step-upped or denied, never executed**,
and the ERP consequence is null.

## What the pilot proves

- A carrier can point an `AssuranceProfileV1` at this action type and get a
  machine verdict (`satisfied` / `step_up` / `deny`) at commit time.
- After execution, a `ClaimsEvidencePackV1` deterministically reconstructs
  *why* the action had effect: identity + authority + state evidence, the REHT
  decision, the RACS clearance digest, the Gateway receipt, and the Veritas
  record — verifiable offline without the worker's chain-of-thought.

## The claimable event (for illustration)

If `SUPPLIER-BETA` fails to deliver and the loss is attributable to a governed
procurement action, the carrier's claims team can take the `ClaimsEvidencePackV1`
and verify, in isolation: the exact action, the coverage condition, the
assurance profile that was in force, and the receipt chain — without needing
access to the agent runtime.

## Sample

- Policy condition: `scenario/policy-condition.yaml`
- Sample profile: `sample-profile/high-value-procurement.json`
- Sample claims pack: `sample-claims-pack/high-value-procurement-claims-pack.json`

> The sample assets are synthetic (mock ERP and mock authorizer) for
> carrier-facing demonstration. Real artifacts come from the shadow pilot.
