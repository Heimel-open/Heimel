# External validation — Accountability at Machine Speed (2026)

Status: External conceptual validation; non-normative.

Source: Brad Wolfe, with Paul Mathieu, Ishaan Ghosh, and Prashant Rajpal, *Accountability at Machine Speed: Four Layers, Four Signatures*, cleared for publication 2026-07-22.

This note records independent convergence between the source's four-layer model and VALO's execution-authorization architecture. The source is not a dependency, does not define REHT semantics, and does not validate the implementation by itself.

## What the source establishes

The paper separates machine-speed accountability into four distinct control problems:

1. **Boundary** — what the machine may decide and under which authority. Task instructions do not create decision authority; missing authority may not be manufactured by inference. Valid prior steps do not accumulate into broader authority, and authority expires when its granting conditions cease to hold.
2. **Machinery** — enforcement at the point where a proposal becomes a consequential write/effect. Missing proof fails closed. Authorization is bound to the specific effect and represented as a single-use grant; an unconsumed or mismatched write must not be reported as successful execution.
3. **Evidence** — contemporaneous proof that the control was operating when the consequential action occurred. Evidence is born at execution rather than reconstructed later from logs.
4. **Seat** — the accountable human/principal retains standing to see, reopen/revoke, and act while the consequence is still reversible. This residual judgment role is not automated away.

The paper's useful architectural shorthand is persistent governance with ephemeral authority: the control architecture persists, but executable authority must be re-established under current conditions after expiry, revocation, stale evidence, dependency change, or material context change.

## Mapping to VALO

The convergence is structural rather than terminological:

- **Boundary** maps to explicit authority/state inputs and REHT's deterministic, action-specific authorization decision. REHT remains the sole execution-authorization boundary.
- **Machinery** maps to REHT -> deterministic RACS binding -> Gateway/adapter enforcement. The enforcement layer may execute only a valid permit and may not broaden authority.
- **Evidence** maps to Veritas execution receipts and verified outcome/state handoff. A workflow completion claim is not equivalent to proof of the real side effect.
- **Seat** maps to Human in the Lead / the accountable principal outside the automated authorization machinery. Automated controls inform and arm that role; they do not replace it.

This source therefore supports the existing VALO separation between authority, authorization, mechanical enforcement, evidence, and accountable human judgment. It does not collapse those responsibilities into one generic governance layer.

## Requirements adopted or sharpened

### 1. Ephemeral authority

Executable authority is never durable by workflow momentum, precedent, prior approval, repeated execution, or an authenticated session. Every consequential execution must still satisfy current authority, scope, purpose, state, constraints, freshness, and applicable evidence requirements.

Expiry, revocation, authority drift, stale evidence, broken causal continuity, or material context change requires fresh authorization. Renewal is a new authorization decision, not continuation under the old permit.

### 2. Single-use, effect-bound execution permit

A permit must be bound to the exact action/effect and execution attempt. The enforcement layer must reject mismatched action/clearance/authority bindings and reject reuse of a consumed permit before invoking the external tool.

Permit consumption is part of the enforcement boundary, not an optional audit step. A failed external invocation still consumes the attempt-specific permit and produces a failure record rather than leaving the same permit available for replay.

Current cross-repo implementation evidence at adoption time:

- `nsolland/valo-gateway@56501e3083be46a6f2a4028bd6f99121ce6d08b6/tests/test_gateway.py` — successful execution consumes the permit; replay of an already-consumed permit is rejected before tool invocation.
- `nsolland/valo-gateway@56501e3083be46a6f2a4028bd6f99121ce6d08b6/tests/test_gateway_core.py` — failed external calls consume the permit and produce a failure receipt; binding mismatches fail closed.

REHT itself may remain deterministic/stateless because single-consumption is an enforcement responsibility. REHT must, however, bind the permit artifact to the exact action and current execution context; Gateway/adapter must consume that permit atomically for the consequential attempt.

### 3. Evidence born with execution

For consequential side effects, post-hoc logs are insufficient as the primary proof that authorization and enforcement held. The execution path must emit a contemporaneous receipt that distinguishes intended action, authorization, enforcement attempt, actual execution result, and verified resulting state where available.

### 4. Human principal remains explicit

No automated layer may claim to eliminate the accountable human/principal role. The system must preserve a route for current signals to reach a principal with standing to revoke/reopen authority and intervene before an irreversible consequence where the operating model requires that capability.

## Relationship to EAR v1

This convergence strengthens the interpretation of existing EAR v1 invariants rather than creating a new layer:

- EA-01 exact action binding
- EA-02 current authority only
- EA-04 causal continuity
- EA-05 non-existence on authority drift
- EA-06 multi-hop reauthorization
- EA-07 temporary authority cannot persist
- EA-08 evidence as an authorization input when required
- EA-11 attempt-bound gates
- EA-14 replay resistance and single-consumption enforcement
- EA-15 external execution result integrity
- EA-16 mechanical enforcement
- EA-20 verifiable execution receipts

## Claims boundary

The paper contains legal and statutory analysis, including discussion of SOX, Caremark, and US tax law. VALO does not adopt those passages here as legal advice, legal conclusions, compliance claims, or product certification claims. Their role in this note is limited to explaining why the authors distinguish the accountable human/principal from the automated control machinery.

The source independently supports the shape of the problem. VALO's implementation claims remain limited to what its code, tests, receipts, formal evidence, and deployment boundaries can actually demonstrate.
