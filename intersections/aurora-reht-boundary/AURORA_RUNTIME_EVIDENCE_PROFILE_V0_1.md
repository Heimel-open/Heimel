# Aurora-Lens runtime evidence profile v0.1

Title: Aurora-Lens 3.0.0 runtime evidence profile for REHT
Author: Njål Solland
Original IP owner: Margaret Stokes retains Aurora-Lens pre-existing IP; VALO Research owns this interoperability profile and adapter mapping
Contributors: Margaret Stokes — source framework and supplied verification materials; review pending
Status: draft
Based on: supplied Aurora-Lens 3.0.0 offline verification bundle, black-box acceptance tests, verification report and public consequence-boundary materials
Changes from prior version: replaces purely abstract Aurora snapshot assumptions with an evidence-backed observable runtime profile
Permitted use: joint research and VALO interoperability work only; no licence or ownership transfer of Aurora-Lens
Related synthesis: `INTERFACE_PROFILE_V0_1.md`

Content type: VALO-ANVENDELSE / proposed shared boundary clarification

## Purpose

This document records only the Aurora-Lens behavior that VALO can observe and bind without importing, copying or redefining Aurora-Lens internals.

The aim is to make the Aurora/REHT boundary executable while keeping both systems independent.

## Evidence baseline

The supplied offline verifier identifies:

- package: `aurora_lens-3.0.0-py3-none-any.whl`;
- SHA-256: `ce195379811921d00263c3d6cef7672d97a12dec6d260c706d3d0bc5ba09ea37`;
- checksum verification: 72 files checked, PASS;
- acceptance tests: 6 passed, 0 failed;
- verified behaviors: pre-LLM independence, post-LLM interception, pass-through, streaming non-release/release and audit verification.

This profile does not claim those tests certify all deployments or all Aurora-Lens semantics.

## Observable contract

The supplied verifier exercises `POST /v1/chat/completions` and reads a top-level `aurora` object from non-streaming responses and streaming SSE events.

Observed fields used by the tests include:

```text
aurora.governance
aurora.llm_called
  compatibility: aurora.llm_invoked
aurora.pre_llm_blocked
  compatibility: blocked_phase == pre_generation
aurora.blocked_phase
aurora.release_path
```

Correlation is exposed through response headers:

```text
aurora-trace-id
aurora-audit-id
```

The verifier separately checks audit rows and an audit verification endpoint for verified chain/HMAC integrity.

## Observable outcome set

The current VALO interoperability profile recognizes the following Aurora outcome labels where present in supplied verification/public material:

```text
PASS
SOFT_CORRECT
FORCE_REVISE
CONTAIN
HARD_STOP
ASK
STOP   # compatibility label observed by supplied tests as accepted non-admit
```

VALO does not redefine the internal meaning of these labels.

## REHT boundary mapping

The mapping rule is deliberately narrow:

```text
Aurora runtime outcome
        ↓
observable evidence record
        ↓
VALO ActionEnvelope governance input
        ↓
REHT authorization
```

Aurora does not emit a REHT or RACS decision.

For the current candidate:

- `PASS` does not preclude REHT evaluation, but is not authorization;
- `SOFT_CORRECT` remains usable as a qualified/review-visible input;
- `FORCE_REVISE` requires a revised candidate and fresh Aurora evaluation before execution authorization;
- `CONTAIN` prevents the current candidate from progressing;
- `HARD_STOP` is preserved as a terminal non-admit for the governed candidate;
- `ASK` preserves suspended/clarification-required state and is not executable;
- `STOP` is treated fail-closed as a compatibility non-admit label.

Any explicitly failed audit-integrity evidence is also non-usable for executable REHT evaluation.

## Freshness and binding

An Aurora runtime observation is not a standing permission.

VALO binds it to the exact `ActionEnvelope` through the VALO-owned `execution_envelope_hash` and gives the observation a short use-time validity window.

Any change in action parameters, governance inputs or bound execution state after adaptation produces a hash mismatch and requires fresh evaluation.

This binding belongs to VALO. It does not change Aurora-Lens internals.

## Data minimisation

The VALO runtime adapter retains only governance metadata needed for the boundary:

- outcome;
- trace/audit references;
- pre/post-LLM execution facts;
- blocked/release path;
- explicit audit-integrity flags when available;
- provider/schema version;
- deterministic fingerprint of that observed metadata.

Candidate text and application payload content are deliberately excluded from the adapter evidence object.

## Licensing boundary

The supplied Aurora-Lens CLI identifies the runtime as `AGPL-3.0-or-commercial` and states that commercial licensing is required for closed-source, SaaS, hosted, embedded, internal proprietary or enterprise use.

Accordingly:

- this profile does not copy or redistribute Aurora-Lens source or binaries;
- the VALO implementation is a black-box interoperability adapter;
- running or distributing Aurora-Lens itself remains subject to Margaret Stokes' applicable licence terms;
- no licence grant is inferred from technical interoperability.

## Implementation reference

VALO production implementation: `nsolland/valo-platform`, `AuroraLensRuntimeAdapter`.

The implementation should remain replaceable by any future mutually agreed profile without changing REHT's authority boundary.

## Review questions for Margaret

1. Are the outcome labels above correctly represented as observable runtime outcomes/compatibility labels?
2. Is `HARD_STOP` correctly preserved as terminal for the current governed route/candidate?
3. Is `ASK` correctly represented as non-executable pending clarification or re-attestation?
4. Are there additional stable correlation fields beyond trace/audit IDs that should be preserved at the interoperability boundary?
5. Is any field listed here implementation-private rather than contract-safe?
