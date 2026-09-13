# Staying Human with AI — governance-gate adoption

Status: adopted architecture guidance
Date: 2026-08-17
Source: Dr. Paul Gromball, *Staying Human with AI*, first edition, TMG KI-Labor Munich / Value Management Practice.

## Source-derived pattern

The useful operational pattern is the governance gate around consequential action. The source defines five practical elements for a gate: a trigger, approval criteria, a named decider, an escalation path, and an auditable record. It also treats negative review as a real control outcome rather than process friction: an unresolved or negative result is not a valid approval.

The source also gives useful gate-placement intuition: human impact, difficult reversibility and material harm are reasons to insert a gate. Its broader human-centered guardrails remain substantive policy choices; they are not imported into REHT as universal authorization rules.

## VALO / REHT adoption

REHT adopts the gate anatomy as an optional human/organizational conformance profile around the existing EA-11 gate mechanism:

```text
Trigger
-> Criteria
-> Authorized Decider
-> Escalation
-> Record
-> REHT validates the gate condition together with current authority
```

This does not move authority to the approver or to the gate. A human approval remains a verified condition/evidence item. REHT still independently requires current identity, authority, scope, purpose, action continuity, nonce binding and every other applicable execution-authorization invariant.

## Machine-checkable profile

An EAR v1 action may select:

```text
governance_gate_profile = EAR_GOVERNANCE_GATE_V1
```

When selected, at least one `human_approval` or `dual_control` gate is required, even if the action would otherwise be MEDIUM and reversible.

The corresponding typed gate attestation must additionally carry:

- `trigger_ref` — the policy/action/threshold condition that caused the gate;
- `criteria_results` — explicit criterion references with `YES`, `NO` or `PARTLY` results;
- `decision = APPROVE` — an explicit positive decision;
- `escalation_ref` — the route used when the decider doubts or refuses;
- `record_ref` — the auditable decision record.

Existing REHT approver-authority checks continue to prove the authorized decider independently of the execution actor.

All criteria must be `YES` for the current execution attempt to proceed. `NO`, `PARTLY`, refusal, missing evidence or malformed gate state fails closed for that attempt. Remediation may produce a new action/gate/attempt; an earlier failed review is never silently converted into approval.

## What is deliberately not adopted into REHT core

The source's five substantive human-centered guardrails are valuable policy inputs, but REHT remains generic. Domain policy, social values, risk interpretation and substantive review criteria belong upstream or in explicit policy/contracts. REHT validates that the required gate was properly formed, authorized, current and affirmative; it does not invent the criteria.

Likewise, the source does not define fresh machine authority state, delegation/revocation semantics, exact action hashes, execution nonces, single governed effect paths or verifiable effect/outcome receipts. Those remain REHT/VALO-native controls.

## Canonical position

`HUMAN_GATE_COMPLETENESS`

A human governance gate can satisfy an execution condition only when its trigger, criteria, authorized decider, escalation route and audit record are explicit, the review is fully affirmative, and the gate remains bound to the exact current execution attempt. The gate never creates execution authority.