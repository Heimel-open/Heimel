# Daon US 12,688,261 Execution Authorization Patent Signal

Date: 2026-08-08
Status: P0 adopted patent / competitive research signal
Source: https://patents.justia.com/patent/12688261
Owner: VALO Research

## Signal

Daon Technology has been granted U.S. Patent No. 12,688,261, titled "Methods and systems for authorizing invocation of a tool by an autonomous artificial intelligence agent."

Justia records application 19/552,620 as filed on 2026-02-27 and the patent as granted on 2026-07-21. The listed assignee is Daon Technology. The listed inventors are Raphael A. Rodriguez and Thomas Grissen.

This is a high-priority external signal because the patent places an authorization checkpoint directly in the path between an autonomous agent's requested tool invocation and execution of that invocation.

## Independent-claim core

Claim 1 requires, in summary:

- a request from an autonomous AI agent to invoke a tool associated with a protected resource
- the agent being behaviorally bound to a person
- obtaining a fidelity signal concerning that person-agent bond
- obtaining an integrity signal concerning whether execution behavior is within an expected range for the requested tool
- determining whether policy rules are satisfied at an authorization checkpoint based on at least one of fidelity, integrity, or request context
- when satisfied, generating a machine-verifiable delegation artifact
- the artifact encoding at least a permitted action type, scope, and bounded validity interval
- effecting the tool invocation based on that delegation artifact

Independent claims 10 and 19 recast substantially the same structure as an electronic device and a non-transitory computer-readable medium.

Dependent claims add, among other things:

- tool/API/function/resource/tenant/object/account scope
- rate, concurrency, invocation-count, data-volume, transaction, and side-effect constraints
- short TTL / per-invocation or short-window artifacts
- denial or constrained/down-scoped authorization
- cryptographic binding to execution context
- runtime-attestation-derived signatures or hashes
- nonce/challenge/session binding for replay resistance

## Canonical VALO interpretation

The market signal is strong: execution-time authorization for autonomous agents is now explicit granted-patent territory in the United States.

The patent does not establish that the general idea of "authorization immediately before agent execution" is owned by Daon. Patent scope is determined by the claims and their legal construction, not by the title or abstract.

VALO must therefore track the exact claim structure rather than treating the patent as either irrelevant or automatically blocking.

## Architectural relationship to VALO

Canonical VALO remains:

VAIG
→ REHT
→ RACS
→ external PEP / gateway
→ execution
→ Veritas

- VAIG evaluates evidence, uncertainty and signals. It has no authority.
- REHT is the deterministic execution-authorization boundary. It applies explicit authority, policy, scope, state and evidence to a proposed consequential action.
- RACS is a deterministic decision contract expressing the already-reached outcome.
- The external PEP/gateway mechanically enforces the permit or refusal.
- Veritas records and verifies what actually occurred.

The Daon claim structure is materially narrower in several explicit respects than this general VALO model. Claim 1 requires the autonomous agent to be behaviorally bound to a person and requires both a fidelity signal and an integrity signal to be obtained. Its successful path also requires generation of a machine-verifiable delegation artifact with action, scope and bounded validity, followed by tool invocation based on that artifact.

REHT's canonical authorization semantics do not depend on a universal person-behavioral-bond primitive. REHT evaluates explicit authority and mandate across human, machine and organizational principals and treats probabilistic signals as evidence inputs rather than as authority.

This distinction is architecturally important but is not, by itself, a legal freedom-to-operate conclusion.

## P0 action

1. Preserve and hash all public VALO/REHT material that predates 2026-02-27 and is relevant to execution-boundary authorization, dynamic scope, step-up, receipts, runtime binding or agent tool control.
2. Build a literal claim chart for independent claims 1, 10 and 19 against the current REHT/gateway implementation. Mark each limitation as present, absent, optional or architecturally inapplicable. Do not infer infringement from conceptual similarity.
3. Verify the complete U.S. prosecution record, patent family and any earlier priority claim before treating 2026-02-27 as the legally controlling priority date.
4. Keep the Daon design as a monitored competitor/patent reference in all future REHT FTO and patent-landscape work.

## Product consequence

This patent is external validation of the category VALO has been defining: static identity/session permission is insufficient for autonomous execution; consequential actions require a control point at or immediately before execution.

VALO's differentiation should remain centered on explicit authority and mandate, deterministic REHT clearance, separation of evaluation from authorization, generic principal types, mechanical enforcement, and independent execution evidence rather than on person-agent behavioral fidelity as the governing primitive.

## Adopted classification

Daon US 12,688,261 is classified as:

- P0 patent-landscape signal
- direct adjacent execution-authorization IP
- relevant FTO review target for REHT and gateway work
- market validation for execution-time agent governance
- not evidence, by itself, of infringement or blocking scope

Canonical formulation:

"Daon patents a person-bound, signal-driven delegation checkpoint for agent tool invocation. VALO's REHT is a deterministic authority boundary over explicit mandate, scope, state and evidence. The overlap must be claim-charted, not guessed."
