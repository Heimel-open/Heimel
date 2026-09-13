# Authority Instrumentation™ → REHT interface profile v0.1

Title: Authority Instrumentation™ → REHT interface profile v0.1
Author: Njål Solland
Original IP owner: Elsa for Authority Instrumentation™; VALO Research for the adapter mapping and REHT contract
Contributors: Elsa — review and approval pending
Status: draft
Based on: prior Authority Instrumentation™ / REHT boundary discussions
Changes from prior version: initial profile
Permitted use: internal joint research and provisional VALO adapter implementation; no transfer, assignment or implied licence of Elsa's pre-existing IP
Related synthesis: `../reht-framework-adapters/BOUNDARY_RULES_V0_1.md`

Content type: VALO-ANVENDELSE and proposed FELLES SYNTESE

## Purpose

This profile defines a narrow translation boundary between Authority Instrumentation™ and VALO/REHT.

It does not merge the two frameworks and does not introduce Authority Instrumentation™ as a required VALO component.

Authority Instrumentation™ supplies structured authority evidence. REHT remains the only VALO execution-authorization boundary.

## Ownership boundary

Elsa owns the concepts, terminology and framework semantics of Authority Instrumentation™.

VALO Research owns:

- the VALO `ActionEnvelope` contract;
- the adapter implementation;
- the mapping into VALO governance inputs;
- REHT evaluation and authorization semantics;
- RACS decisions and Veritas receipts.

The adapter must not reinterpret, extend or infer authority beyond the input supplied by Authority Instrumentation™.

## Provisional input profile

The exact external field names remain subject to Elsa's approval. The VALO adapter accepts a provider-neutral snapshot with these minimum semantics:

```json
{
  "assessment_id": "ai:authority:123",
  "provider_id": "authority-instrumentation",
  "subject_id": "agent-123",
  "mandate_ref": "mandate:finance:7",
  "scope": {"payment_limit": 10000, "currency": "EUR"},
  "context": {"workflow": "supplier-payment"},
  "exposure": {"class": "high"},
  "issued_at": "2026-08-07T04:00:00Z",
  "valid_until": "2026-08-07T04:05:00Z",
  "revoked": false,
  "revocation_ref": null,
  "human_authority_ref": "authority:controller:44",
  "source_refs": ["policy:payments:v3"],
  "fingerprint": "sha256:..."
}
```

## Adapter output

The adapter may populate only provider-neutral VALO fields:

- `governance_inputs[]` with domain `authority`;
- `authority_refs[]`;
- `authority_fingerprint`;
- explicit delegation scope;
- non-authoritative adapter metadata for traceability.

It must never emit an `ALLOW`, `MODIFY`, `DEFER`, `DENY`, `STEP_UP` or `HALT` decision.

## Required invariants

1. Subject binding is exact. A snapshot for another actor or delegation cannot be reused.
2. Time is evaluated at use, not only at issuance.
3. Revocation is binding immediately.
4. Missing or malformed authority evidence is not repaired by inference.
5. Scope may be preserved or narrowed, never broadened by the adapter.
6. The source fingerprint is retained so a changed authority snapshot invalidates prior evaluation.
7. REHT may deny even when the authority snapshot is valid.
8. A valid authority snapshot does not itself authorize execution.

## Fail-closed behaviour

The adapter returns a preclusive binding result when the snapshot is:

- expired;
- revoked;
- bound to a different subject;
- missing a mandate reference;
- missing a source fingerprint;
- structurally invalid.

Preclusion means the input cannot support authorization. It is not an independent authorization decision.

## No new component

The adapter is a library boundary inside the canonical VALO runtime. It does not create a new service, authority engine or external runtime dependency.

## Approval required

Before this profile becomes `accepted`, Elsa must confirm:

- whether the provisional fields preserve Authority Instrumentation™ semantics;
- the authoritative vocabulary for mandate, scope, context, exposure, time and revocation;
- whether any fields must remain opaque references rather than copied values;
- permitted implementation and licensing terms.
