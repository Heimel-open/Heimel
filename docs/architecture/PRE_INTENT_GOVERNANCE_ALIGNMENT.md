# Pre-Intent Governance Alignment

## Status

VAIG has a pre-intent governance layer.

Previous model:

Reality -> Intent -> Authorization -> Action

Current wider governance context:

Reality -> Evidence -> EvidenceCondition -> Intent -> Authority Context -> Admissibility -> Action/Refusal -> Accountability Thread -> Receipt

This is not one formal object.

## Architectural Position

EvidenceCondition belongs to VAIG Core as a pre-intent gate.

It is not part of the VALO TLA execution core.

It is also not a deployment mode, proxy feature, MCP feature, sidecar feature, or wrapper feature.

Proxy, MCP, Sidecar and Wrapper remain deployment modes around shared VAIG Core.

## Boundary

VALO TLA / L1 Guardian covers bounded execution-state governance.

It covers state, degraded mode, halt, reset, audit append, and terminal log-full halt.

It does not determine human standing, organizational legitimacy, value-chain coherence, general epistemology, or long-term organizational continuity.

Those inputs are supplied by external authority, policy and organizational-governance systems and remain outside the formal execution core.

Historical collaboration frameworks may be referenced in archived research material, but they are not runtime dependencies of VALO Core.

## Governance Layers

Layer 0 — Reality & Evidence

Context and input assumptions. Outside TLA core.

Layer 1 — Evidence Admissibility

VAIG Core pre-intent gate. EvidenceCondition lives here.

Layer 2 — Intent Formation

VALO Harness / application layer.

Layer 3 — Authority and Admissibility Context

VAIG and REHT consume authority, policy, delegation and evidence inputs.

Layer 4 — Execution Governance

VALO TLA / L1 Guardian where applicable.

Layer 5 — Accountability

Accountability Thread, RACS contract and receipt.

Layer 6 — Human and Organizational Authority

External accountable roles, delegated authority sources and organizational governance. Outside TLA core.

## Verified Invariant Candidate

A pre-intent invariant may be specified separately as:

No intent may become an executable action candidate unless EvidenceCondition status is VALIDATED or explicitly OVERRIDDEN by a recognized authority path.

Blocked statuses: SUBMITTED, STALE, CONTESTED, INSUFFICIENT.

This should not be merged into `ValoStateMachine.tla` unless it is translated into bounded state-machine variables and checked with matching implementation and test vectors.

## Governance Questions

VAIG Core may ask:

Was the action candidate formed from admissible evidence and a valid authority context?

REHT asks:

Is the proposed action admissible in the current state?

VALO TLA asks only:

Is the bounded execution-state transition allowed?

Keep those questions separate.
