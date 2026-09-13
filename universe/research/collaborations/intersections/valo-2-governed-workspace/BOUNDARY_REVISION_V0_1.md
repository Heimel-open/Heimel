# VALO 2.0 Governed Workspace research boundary revision v0.1

Title: VALO 2.0 Governed Workspace research boundary revision v0.1
Author: Njål Solland
Original IP owner: Margaret Stokes retains Aurora-Lens and PEF-related pre-existing IP; Elsa retains Authority Instrumentation™ pre-existing IP; Njål Solland / VALO Research owns the proposed VALO-side architecture and implementation mapping
Contributors: Margaret Stokes and Elsa — review and approval pending; OpenAI coding assistance under Njål's direction
Status: draft
Based on: existing Aurora-Lens/REHT and Authority Instrumentation™/REHT profiles; issue #5; VALO Governed Workspace implementation as of 12 August 2026; Margaret Stokes PEF specification SHA-256 `471aa6cb6904c1057597706d63befcf880629c403c487e03dd3d4d4b46b2e200`
Changes from prior version: proposes the first shared boundary revision after VALO governance moved from worker-centric control to a Kernel-derived Governed Workspace
Permitted use: internal joint research and explicit owner review; provisional VALO-side architecture work only; no transfer, assignment, licence or implementation right for Margaret's or Elsa's pre-existing IP is implied
Related synthesis: `../reht-framework-adapters/BOUNDARY_RULES_V0_1.md`; `../aurora-lens-reht/INTERFACE_PROFILE_V0_1.md`; `../authority-instrumentation-reht/INTERFACE_PROFILE_V0_1.md`; `REVIEW_CHECKLIST_V0_1.md`

Content type: proposed FELLES SYNTESE and VALO-ANVENDELSE. This document is
not accepted and creates no authority or admissibility inside VALO.

## Proposal in one sentence

Margaret and Elsa can provide governed inputs to VALO's representation and
authorization process, but the worker receives only a Kernel-compiled bounded
world; external admission can never become Kernel truth without evidence
admission, and external authority evidence can never become positive clearance
without current Kernel state and REHT authorization.

## Revised topology

```text
Optional external research-framework results
  Margaret / Aurora-Lens: standing, evidence admission, persistent state,
                          communication admissibility, scoped non-admit
  Elsa / Authority Instrumentation: mandate, scope, context, exposure,
                                    time, revocation, human authority
                    |
          provider-neutral VALO mapping
                    |
          +---------+-------------------+
          |                             |
          v                             v
Kernel evidence/state path       exact-action preclusive path
admit with provenance            attach immutable fingerprint/scope
and dependency binding           to action governance evidence
          |                             |
          v                             |
Kernel authoritative governed representation
          |
purpose/scope/capability-bounded Governed Workspace
          |
replaceable worker -> candidate -> deterministic conformance
          |
fresh sealed Kernel execution context ----------------+
                                                      |
                                                      v
                                                    REHT
                                                      |
                                             RACS -> Gateway -> Veritas
```

The two paths are deliberately different:

1. An external input that changes what VALO represents as the current world
   must enter through Kernel evidence admission and a canonical event. Its
   source fingerprint becomes a relevant workspace dependency.
2. An external result may remain outside Kernel state when its only force is to
   narrow, preclude or require review for one exact action. In that case it is
   bound to the exact action/workspace/context digests and evaluated by REHT.
   It cannot create a positive fact, authority or clearance.

## Margaret / Aurora-Lens

This proposal preserves the existing external and optional topology.
Aurora-Lens is not a VALO runtime component. A VALO-side consumer may preserve
the external result as governance evidence.

### State-shaping use

- `standing`, admitted evidence and persistent-state results may be submitted
  to Kernel as evidence with the original assessment ID, provider schema,
  source fingerprint, evidence/state refs, validity, contradictions and
  unresolved refs.
- Kernel's normal verify/admit/event path decides whether a derived fact or
  state transition can enter the governed representation.
- An Aurora `PASS`, `SOFT_CORRECT` or provider-neutral `admit` is not itself a
  `CONFIRMED` Kernel fact.
- If admitted content is projected into a workspace, the external fingerprint
  and resulting Kernel objects are material dependencies. A changed
  fingerprint invalidates reuse of the prior workspace result.

### Exact-action preclusive use

- Scoped `non_admit`, `CONTAIN`, `FORCE_REVISE`, `HARD_STOP` or
  communication-inadmissibility can remain a binding preclusive input for the
  covered action without first becoming Kernel truth.
- The scope, fingerprint, assessment ID and validity must be bound to the
  exact action envelope, workspace binding and fresh Kernel context.
- REHT may deny in addition to Aurora-Lens. It cannot convert a binding
  non-admit into admissibility.
- Aurora-Lens never receives VALO execution authority.

### PEF distinction

The reviewed PEF specification is related to Margaret's work but is not
silently equated with the existing Aurora-Lens interface profile. Subject to
Margaret's approval, PEF may be evaluated as an optional cognitive-frame
profile inside one Governed Workspace:

- current content is rendered as an active bounded present;
- reconstructed and projected content is explicitly labelled and retains
  provenance;
- relational operators are compiled constraints;
- collapse expires worker activation and emits a receipt;
- Kernel/reht still retain event order, timestamps, validity, expiry,
  revocation, replay and audit.

No-temporal-tracking is therefore a possible worker presentation rule, not a
governance-plane invariant.

## Elsa / Authority Instrumentation™

Authority Instrumentation supplies structured authority evidence. It does not
issue REHT clearance.

### Kernel authority-state use

- A snapshot that is intended to support positive authority must be admitted
  or synchronized into Kernel as a tenant-bound authority/delegation record
  with subject, mandate, purpose, scope, constraints, validity, revocation,
  human-authority ref, source refs and source fingerprint.
- The worker does not receive authority, delegation or identity collections in
  its workspace projection.
- At authorization, Kernel resolves current authority into the sealed
  execution context and REHT independently checks exact actor, capability,
  target, purpose, time and revocation.
- A structurally valid Elsa snapshot is insufficient if Kernel has no current
  matching authority state.

### Direct narrowing/preclusion use

- A revoked, expired, cross-subject or scope-incompatible snapshot can
  preclude use of stale authority evidence for the exact action.
- Direct adapter input may preserve or narrow scope, never broaden it.
- A direct snapshot cannot repair missing Kernel authority, create a new
  delegation or produce `ALLOW`.
- Immediate revocation requires both preclusion at REHT and prompt canonical
  Kernel state update. The preclusive path closes the race; the Kernel event
  restores the authoritative representation.

## Governed Workspace binding revision

When either research framework affects a workspace-originated action, the
adapter result should extend the existing action-specific binding with:

```json
{
  "provider_id": "...",
  "assessment_id": "...",
  "profile_version": "...",
  "provider_schema_version": "...",
  "source_fingerprint": "sha256:...",
  "bound_action_id": "...",
  "bound_workspace_binding_digest": "sha256:...",
  "bound_kernel_context_digest": "sha256:...",
  "bound_purpose_ref": "...",
  "binding_scope": "...",
  "valid_until": "...",
  "preclusive": false,
  "preclusive_reason": null,
  "review_required": false,
  "review_reasons": []
}
```

The pair `bound_workspace_binding_digest` and `bound_kernel_context_digest` is
atomic. Any action, worker result, relevant state, purpose, authority,
external fingerprint or proof change requires a new evaluation.

The adapter does not sign RACS artifacts. RACS transports the resulting
bindings; REHT owns the decision; Gateway enforces exact equality; Veritas
records what was observed.

## Jasper / IAB unresolved boundary

Njål identified Jasper/IAB as relevant to the VALO 2.0 placement question, but
no owned Jasper/IAB source, repository or interface profile was located in the
available collaboration or VALO repositories during this revision.

No normative semantics are therefore asserted here. A possible placement near
the exact action/workspace/authority binding must remain a hypothesis until an
owned source defines:

- what IAB stands for and which object it binds;
- whether it supplies evidence, state, authority, conformance or transport;
- who owns the semantics and may approve the mapping;
- validity, revocation and failure behavior;
- whether the output can narrow/preclude, and an explicit statement that it
  cannot widen REHT clearance.

No runtime adapter should be built from the name alone.

## Acceptance and implementation boundary

This draft changes no prior research profile and no production runtime. If the
affected owners accept the synthesis, implementation belongs in canonical VALO
product repositories through separate HIGH-risk issues and pull requests.

Margaret and Elsa approval is required before any statement about their
framework semantics moves from `draft` to `accepted`. Njål remains accountable
for VALO-side architecture, code, security review and authorization behavior.

