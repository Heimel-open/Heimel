# Aurora-Lens → REHT interface profile v0.1

Title: Aurora-Lens → REHT interface profile v0.1
Author: Njål Solland
Original IP owner: Margaret Stokes for Aurora-Lens; VALO Research for VALO-side mapping and REHT contract
Contributors: Margaret Stokes — review and approval pending
Status: draft
Based on: prior Aurora-Lens / REHT boundary discussions; external adapter topology clarified 11 August 2026
Changes from prior version: corrected topology so Aurora-Lens and its adapter remain external and optional; VALO owns only its own downstream client mapping
Permitted use: internal joint research and provisional external integration work; no transfer, assignment or implied licence of Margaret's pre-existing IP
Related synthesis: `../reht-framework-adapters/BOUNDARY_RULES_V0_1.md`; `../aurora-external-adapter/EXTERNAL_ADAPTER_CONTRACT_V0_1.md`
External alignment evidence: `OECD_ALIGNMENT_EVIDENCE_2026-02-21.md`

Content type: VALO-ANVENDELSE and proposed FELLES SYNTESE

## Purpose

This profile defines how VALO may consume an Aurora-Lens result when VALO independently chooses to call the external Aurora-Lens service.

Aurora-Lens and its external adapter/runtime are not part of VALO. The topology is:

`VALO -> external Aurora-Lens service/adapter -> Aurora result -> VALO-side mapping -> REHT`

VALO may also choose not to call Aurora-Lens.

Aurora-Lens supplies standing, evidence-admission, persistent-state and communication-admissibility inputs when called. REHT remains the only VALO execution-authorization boundary.

A lack of admissibility is not an authorization decision. It means REHT lacks a valid basis on which to authorize the covered consequence.

## Ownership boundary

Margaret Stokes owns the concepts, terminology, framework semantics and proprietary runtime of Aurora-Lens.

VALO Research owns its own downstream components, including:

- the VALO `ActionEnvelope` contract;
- the VALO-side client/mapping from an external Aurora result into VALO governance inputs;
- REHT evaluation and authorization semantics;
- RACS decisions and Veritas receipts.

Nothing in this profile asserts VALO ownership of the Aurora-Lens service, external adapter/runtime, or Margaret's implementation.

The VALO-side mapping must preserve Aurora-Lens outputs as supplied. It must not resolve contradictions, invent standing, admit excluded evidence or repair unresolved references.

## Provisional input profile

The exact external field names remain subject to Margaret's approval. A VALO-side consumer may accept a provider-neutral snapshot with these minimum semantics:

```json
{
  "assessment_id": "aurora:standing:123",
  "provider_id": "aurora-lens",
  "subject_ref": "case:supplier-payment:9",
  "standing": "established",
  "evidence_admission": "admit",
  "evidence_refs": ["evidence:invoice:7"],
  "state_ref": "aurora-state:44",
  "unresolved_refs": [],
  "contradiction_refs": [],
  "communication_admissible": true,
  "non_admit": false,
  "binding_scope": "irreversible_downstream",
  "issued_at": "2026-08-07T04:00:00Z",
  "valid_until": "2026-08-07T04:05:00Z",
  "fingerprint": "sha256:..."
}
```

The separate external adapter contract records the currently observable v3.0.1 wire surface and native governance vocabulary.

## VALO-side output

If VALO calls Aurora-Lens, the VALO-side mapping may populate only provider-neutral VALO fields:

- `governance_inputs[]` with domains such as `standing`, `evidence_admission`, `persistent_state` or `communication_admissibility`;
- `evidence_refs[]`;
- `evidence_fingerprint`;
- `state_fingerprint`;
- non-authoritative client metadata for traceability.

It must never emit a RACS decision on behalf of Aurora-Lens.

## Required invariants

1. Calling Aurora-Lens is optional from VALO's perspective.
2. Standing is represented, never invented by the VALO-side mapping.
3. Evidence excluded or not admitted by Aurora-Lens is not silently reintroduced.
4. Contradictions and unresolved references remain visible to REHT.
5. A changed persistent-state fingerprint invalidates prior evaluation.
6. A `non_admit` output is binding within its declared scope when the Aurora contract states that force.
7. REHT may deny in addition to an Aurora-Lens admission.
8. REHT cannot convert missing admissibility into admissibility.
9. Aurora-Lens does not gain execution authority through being called.
10. No Aurora-Lens code, policy engine or proprietary runtime is required inside VALO.

## Binding non-admit rule

The provisional default scope is `irreversible_downstream`.

When `non_admit=true`, the VALO-side mapping returns a preclusive binding input for actions that are irreversible or whose reversibility is unknown. The action cannot proceed to executable authorization on that evidence state.

If `binding_scope=all_downstream`, preclusion applies to every covered action.

For communication actions, `communication_admissible=false` is preclusive regardless of general evidence admission.

Preclusion is an admissibility boundary, not an independent authority decision.

## Fail-closed behaviour

The VALO-side mapping returns a preclusive result when the received snapshot is:

- expired;
- missing a required source fingerprint;
- structurally invalid;
- `non_admit` within the declared binding scope;
- communication-inadmissible for a communication or disclosure action.

Unresolved references and contradictions are preserved as explicit review-required signals. They are not auto-resolved.

If the external Aurora-Lens service is unavailable or the response cannot be validated, VALO treats Aurora evidence as unavailable. VALO does not fabricate an Aurora admission.

## External component boundary

Aurora-Lens is an independent external runtime/service. Its adapter is part of that external callable boundary, not a library inside the canonical VALO runtime.

VALO's only implementation responsibility under this profile is a thin optional client/mapping that can call the external service, validate the response and preserve it into VALO inputs. This creates no ownership, authority or admissibility inside VALO for Aurora-Lens itself.

## Approval required

Before this profile becomes `accepted`, Margaret must confirm:

- whether the provisional fields preserve Aurora-Lens semantics;
- the exact standing and evidence-admission vocabulary;
- the scope and force of `non_admit`;
- treatment of contradictions, unresolved references and communication admissibility;
- which fields must remain opaque references;
- the external adapter/service contract and permitted implementation/licensing terms.
