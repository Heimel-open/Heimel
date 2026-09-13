# REHT research-framework adapter boundary rules v0.1

Title: REHT research-framework adapter boundary rules v0.1
Author: Njål Solland
Original IP owner: each framework owner retains pre-existing IP; VALO Research owns the adapter architecture and REHT contract
Contributors: Margaret Stokes and Elsa — review and approval pending
Status: draft
Based on: Aurora-Lens / REHT and Authority Instrumentation™ / REHT boundary discussions
Changes from prior version: initial shared boundary proposal; added exact execution-envelope binding
Permitted use: internal joint research and provisional VALO implementation; no transfer or implied licence of pre-existing IP
Related synthesis: `../authority-instrumentation-reht/INTERFACE_PROFILE_V0_1.md`, `../aurora-lens-reht/INTERFACE_PROFILE_V0_1.md`

Content type: proposed FELLES SYNTESE and VALO-ANVENDELSE

## Decision proposed for review

The collaboration repo holds research contracts, terminology, attribution and conformance examples.

It does not hold production runtime code and creates no authority inside VALO.

The production adapters live in a canonical VALO product repo and consume versioned, provider-neutral snapshots from each framework.

## Canonical separation

```text
Aurora-Lens
  standing · evidence admission · persistent state · communication admissibility
                         ↓
                  Aurora adapter
                         ↓
Authority Instrumentation™
  mandate · scope · context · exposure · time · revocation · human authority
                         ↓
                 Authority adapter
                         ↓
                    ActionEnvelope
                         ↓
                         REHT
                         ↓
                         RACS
                         ↓
                 external enforcement
                         ↓
                       Veritas
```

The arrows are input and translation boundaries. They are not transfers of ownership or decision authority.

## Common adapter contract

Every adapter result must contain:

```json
{
  "provider_id": "...",
  "assessment_id": "...",
  "source_fingerprint": "sha256:...",
  "bound_action_id": "...",
  "bound_execution_envelope_hash": "sha256:...",
  "preclusive": false,
  "preclusive_reason": null,
  "review_required": false,
  "review_reasons": [],
  "governance_input_refs": ["..."],
  "adapter_version": "0.1"
}
```

The adapted `ActionEnvelope` and result are separate objects. The binding hash is computed from the exact canonical envelope after the research input has been attached. Any later change to action, actor, target, authority, evidence, state or parameters produces a different hash and invalidates reuse of the prior binding.

The result explains whether the supplied research input is structurally usable and whether a declared non-admit, expiry or revocation blocks use of that input.

## Non-negotiable rules

1. No adapter may emit or impersonate a REHT/RACS decision.
2. No adapter may broaden authority, scope, standing or evidence admission.
3. Invalid input fails closed and remains visible in receipts.
4. Native framework fingerprints are retained.
5. Every binding is action-specific, envelope-specific and versioned.
6. Production code has no mandatory runtime dependency on either external framework.
7. A valid external input is evidence for REHT, never sufficient authorization.
8. A binding admissibility veto is preserved within its declared scope.
9. REHT remains free to deny even when all external inputs are valid.
10. Veritas must be able to record the provider, assessment, source fingerprint, execution-envelope hash, adapter version and resulting REHT decision.

## Versioning

The research interface version and implementation version are independent:

- `profile_version`: agreed research contract;
- `adapter_version`: VALO implementation;
- `provider_schema_version`: native framework output version.

A provider schema change must not silently change the profile mapping.

## Approval boundary

This document is not accepted until Margaret and Elsa approve the portions that describe their respective frameworks.

Approval of this interface profile does not by itself grant commercial, sublicensing or redistribution rights. Those remain separate agreements.
